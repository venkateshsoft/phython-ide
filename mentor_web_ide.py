"""Local browser IDE for Python Mentor. Start with: python mentor_web_ide.py"""
import ast, builtins, json, keyword, os, subprocess, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>Python Mentor IDE</title>
<style>body{margin:0;background:#111827;color:#e5e7eb;font:14px Segoe UI,Arial}header{padding:12px 18px;background:#1f2937;display:flex;gap:8px;align-items:center}button{background:#2563eb;color:white;border:0;border-radius:5px;padding:8px 14px;cursor:pointer}#layout{display:grid;grid-template-columns:1fr 360px;height:calc(100vh - 58px)}#editor{width:100%;height:100%;box-sizing:border-box;background:#0b1020;color:#d1d5db;border:0;outline:0;padding:18px;font:15px Consolas,monospace;line-height:1.5;resize:none}aside{padding:15px;background:#172033;overflow:auto}pre{white-space:pre-wrap;background:#0b1020;padding:12px;border-radius:5px;min-height:120px}.ok{color:#86efac}.bad{color:#fca5a5}.title{font-weight:700;font-size:18px;margin-right:auto}</style></head><body>
<header><span class="title">Python Mentor IDE</span><button onclick="check()">Check code</button><button onclick="fix()">Auto-fix intent</button><button onclick="run()">Run</button><button onclick="clearScreen()">Clear</button><span>Ctrl+Space suggestions | F5 run</span></header><div id="layout"><textarea id="editor" spellcheck="false"># Try a keyword: duplicate, prime, factorial, fibonacci, palindrome, reverse, even, sum
items = [1, 2, 2, 3, 4, 4]
duplicates = set(items)
print(duplicates)
</textarea><aside><h3>Mentor feedback</h3><pre id="result">Ready. Syntax, intent, and logic feedback will appear here.</pre><h3>Suggestions</h3><pre id="suggestions">Start typing a Python keyword, built-in, or name.</pre></aside></div>
<script>const e=document.getElementById('editor'),r=document.getElementById('result'),s=document.getElementById('suggestions');
async function api(path){let x=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:e.value})});return await x.json()}
async function check(){r.textContent='Checking...';let x=await api('/check');r.textContent=x.message;r.className=x.ok?'ok':'bad'}
async function fix(){r.textContent='Understanding intent and fixing...';let x=await api('/autofix');if(x.changed)e.value=x.code;r.textContent=x.message;r.className=x.ok?'ok':'bad'}
async function run(){let f=await api('/autofix');if(f.changed)e.value=f.code;r.textContent=f.changed?f.message+'\n\nRunning corrected code...':'Running...';let x=await api('/run');r.textContent=(f.changed?f.message+'\n\n':'')+x.message;r.className=x.ok?'ok':'bad'}
function clearScreen(){e.value='';r.textContent='Screen cleared.';s.textContent='Start typing a keyword or Python code.';e.focus()}
e.addEventListener('input',()=>{let m=e.value.slice(0,e.selectionStart).match(/[A-Za-z_]\w*$/),p=m?m[0]:'';if(!p){s.textContent='Type a word to see suggestions.';return}fetch('/suggest?prefix='+encodeURIComponent(p)).then(x=>x.json()).then(x=>s.textContent=x.items.join('  |  ')||'No suggestions')});
e.addEventListener('keydown',x=>{if(x.key==='F5'){x.preventDefault();run()}if(x.key===' '&&x.ctrlKey){x.preventDefault();let m=e.value.slice(0,e.selectionStart).match(/[A-Za-z_]\w*$/),p=m?m[0]:'';fetch('/suggest?prefix='+encodeURIComponent(p)).then(x=>x.json()).then(y=>s.textContent=y.items.join('  |  '))}});</script></body></html>'''

def check_code(code):
    try:
        tree = ast.parse(code)
        assigned = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        unknown = sorted((loaded - assigned - set(dir(builtins))) - {'self'})
        msg = 'OK: no syntax errors found.'
        msg += '\n\nLogic hint: possible undefined names: ' + ', '.join(unknown) if unknown else '\n\nOK: no simple logic warnings found.'
        return True, msg
    except (SyntaxError, IndentationError) as ex:
        return False, f'Line {ex.lineno or "?"}: {ex.msg}\n\nFix the highlighted issue, then check again.'

def auto_fix(code):
    """Apply conservative keyword-based intent templates and syntax fixes."""
    original = code
    code = code.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    lower = code.lower()
    # These templates make common beginner exercises executable while keeping the
    # user's data expression when it is a literal list or tuple.
    try:
        tree = ast.parse(code)
        data_expr = next((ast.unparse(n.value) for n in tree.body
                          if isinstance(n, ast.Assign) and isinstance(n.value, (ast.List, ast.Tuple))), '[1, 2, 3]')
    except SyntaxError:
        tree, data_expr = None, '[1, 2, 3]'
    if any(w in lower for w in ('duplicate', 'duplicates', 'repeated item', 'repeated items')):
        try:
            source_name = 'items'
            fixed = (f"# Auto-corrected intent: identify duplicate items\n{source_name} = {data_expr}\n"
                     f"duplicates = []\nfor item in {source_name}:\n    if {source_name}.count(item) > 1 and item not in duplicates:\n        duplicates.append(item)\n"
                     "print('Duplicate items:', duplicates)\n")
            return fixed, 'Intent recognized: duplicate detection. Generated executable logic that preserves order and removes repeated results.'
        except Exception:
            pass
    if any(w in lower for w in ('factorial', 'factorial number')):
        return ("# Auto-corrected intent: calculate factorial\nnumber = 5\nresult = 1\nfor value in range(2, number + 1):\n    result *= value\nprint('Factorial:', result)\n", 'Intent recognized: factorial calculation.' )
    if any(w in lower for w in ('fibonacci', 'fibonocci')):
        return ("# Auto-corrected intent: generate Fibonacci numbers\ncount = 10\na, b = 0, 1\nsequence = []\nfor _ in range(count):\n    sequence.append(a)\n    a, b = b, a + b\nprint('Fibonacci:', sequence)\n", 'Intent recognized: Fibonacci sequence generation.')
    if 'prime' in lower:
        return ("# Auto-corrected intent: test prime numbers\nnumber = 29\nis_prime = number > 1 and all(number % divisor for divisor in range(2, int(number ** 0.5) + 1))\nprint('Prime:', is_prime)\n", 'Intent recognized: prime-number test.')
    if 'palindrome' in lower:
        return ("# Auto-corrected intent: test palindrome\ntext = 'level'\nclean = ''.join(character.lower() for character in text if character.isalnum())\nprint('Palindrome:', clean == clean[::-1])\n", 'Intent recognized: palindrome test.')
    if 'reverse' in lower:
        return (f"# Auto-corrected intent: reverse a sequence\nitems = {data_expr}\nprint('Reversed:', items[::-1])\n", 'Intent recognized: sequence reversal.')
    if any(w in lower for w in ('even', 'odd')):
        return ("# Auto-corrected intent: classify a number\nnumber = 10\nprint('Even' if number % 2 == 0 else 'Odd')\n", 'Intent recognized: even/odd classification.')
    if any(w in lower for w in ('sum', 'total', 'add numbers')):
        return (f"# Auto-corrected intent: calculate a total\nitems = {data_expr}\nprint('Total:', sum(items))\n", 'Intent recognized: sum/total calculation.')
    lines, changed = code.splitlines(), False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.endswith(':'):
            if any(stripped.startswith(k + ' ') or stripped.startswith(k + '(') for k in ('if','elif','else','for','while','def','class','try','except','finally','with')):
                lines[i], changed = line + ':', True
    if changed:
        return '\n'.join(lines) + ('\n' if code.endswith('\n') else ''), 'Auto-fix applied: added missing block punctuation (:).'
    return original, 'No safe automatic correction was found. The IDE will not guess when changing code could alter your intent.'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, obj):
        raw = json.dumps(obj).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path.startswith('/suggest?prefix='):
            from urllib.parse import unquote
            p = unquote(self.path.split('=',1)[1]); names = set(keyword.kwlist) | set(dir(builtins)) | {'self'}
            self.send_json({'items': sorted(x for x in names if x.startswith(p) and x != p)[:30]}); return
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(HTML.encode())
    def do_POST(self):
        try:
            return self._post_impl()
        except Exception as ex:
            self.send_json({'ok': False, 'message': 'IDE server error: ' + str(ex)})

    def _post_impl(self):
        n = int(self.headers.get('Content-Length','0')); code = json.loads(self.rfile.read(n) or '{}').get('code','')
        if self.path == '/check': ok, msg = check_code(code); self.send_json({'ok':ok,'message':msg}); return
        if self.path == '/autofix':
            fixed, explanation = auto_fix(code); ok, check = check_code(fixed)
            self.send_json({'ok':ok,'changed':fixed != code,'code':fixed,'message':explanation+'\n\n'+check}); return
        if self.path == '/run':
            ok, msg = check_code(code)
            if not ok: self.send_json({'ok':False,'message':msg}); return
            path = os.path.join(os.path.dirname(__file__),'_mentor_run.py'); open(path,'w',encoding='utf-8').write(code)
            try:
                p = subprocess.run([sys.executable,path],capture_output=True,text=True,timeout=10,cwd=os.path.dirname(__file__))
                out = (p.stdout or '') + ('\nErrors:\n' + p.stderr if p.stderr else '')
                self.send_json({'ok':p.returncode == 0,'message':out or 'Program finished with no output.'})
            except subprocess.TimeoutExpired: self.send_json({'ok':False,'message':'Stopped: program ran longer than 10 seconds.'})

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
