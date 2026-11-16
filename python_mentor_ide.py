"""Python Mentor IDE - a small, dependency-free beginner Python editor."""
import ast
import builtins
import keyword
import os
import re
import subprocess
import sys
import tempfile
import threading
import tokenize
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


PYTHON = sys.executable


class PythonMentorIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Mentor IDE")
        self.geometry("1100x720")
        self.current_file = None
        self.completion_box = None
        self._build_ui()
        self._bind_keys()
        self.editor.insert("1.0", "# Start typing Python here...\n\n")
        self.editor.edit_modified(False)
        self.highlight()

    def _build_ui(self):
        bar = ttk.Frame(self, padding=6)
        bar.pack(fill="x")
        for label, command in (("New", self.new_file), ("Open", self.open_file),
                               ("Save", self.save_file), ("Run", self.run_code),
                               ("Check code", self.check_code)):
            ttk.Button(bar, text=label, command=command).pack(side="left", padx=3)
        ttk.Label(bar, text="  Ctrl+Space: suggestions  |  F5: run  |  Ctrl+S: save").pack(side="left")

        body = ttk.PanedWindow(self, orient="vertical")
        body.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        editor_frame = ttk.Frame(body)
        output_frame = ttk.Frame(body)
        body.add(editor_frame, weight=4)
        body.add(output_frame, weight=1)

        self.editor = tk.Text(editor_frame, undo=True, wrap="none", font=("Consolas", 12),
                              bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
                              selectbackground="#264f78", tabs="    ")
        yscroll = ttk.Scrollbar(editor_frame, command=self.editor.yview)
        xscroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.editor.xview)
        self.editor.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.editor.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        self.output = tk.Text(output_frame, height=8, wrap="word", state="disabled",
                              font=("Consolas", 10), bg="#111827", fg="#d1fae5")
        self.output.pack(fill="both", expand=True)
        self.status = ttk.Label(self, text="Ready", anchor="w", padding=4)
        self.status.pack(fill="x")

        for tag, color in {"keyword": "#c586c0", "string": "#ce9178", "comment": "#6a9955",
                           "number": "#b5cea8", "builtin": "#4ec9b0", "error": "#ff5555"}.items():
            self.editor.tag_configure(tag, foreground=color)
        self.editor.tag_configure("error_line", background="#51202a")

    def _bind_keys(self):
        self.editor.bind("<KeyRelease>", self._on_key)
        self.editor.bind("<Control-space>", lambda e: (self.show_completions(), "break")[1])
        self.editor.bind("<Tab>", self.accept_completion)
        self.editor.bind("<F5>", lambda e: (self.run_code(), "break")[1])
        self.bind("<Control-s>", lambda e: (self.save_file(), "break")[1])

    def _on_key(self, _event=None):
        self.highlight()
        if self.editor.get("insert-1c", "insert")[-1:] in ".(":
            self.show_completions()

    def write_output(self, text, clear=False):
        self.output.configure(state="normal")
        if clear:
            self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def new_file(self):
        self.current_file = None
        self.editor.delete("1.0", "end")
        self.status.config(text="New file")

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", text)
            self.current_file = path
            self.status.config(text=f"Opened {path}")
            self.highlight()
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def save_file(self):
        if not self.current_file:
            self.current_file = filedialog.asksaveasfilename(defaultextension=".py",
                filetypes=[("Python files", "*.py"), ("All files", "*")])
        if not self.current_file:
            return False
        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.editor.get("1.0", "end-1c"))
            self.status.config(text=f"Saved {self.current_file}")
            return True
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return False

    def highlight(self):
        text = self.editor.get("1.0", "end-1c")
        for tag in ("keyword", "string", "comment", "number", "builtin", "error", "error_line"):
            self.editor.tag_remove(tag, "1.0", "end")
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                kind, value, start, end, _ = tok
                tag = {tokenize.NAME: "keyword" if keyword.iskeyword(value) else
                       ("builtin" if value in dir(builtins) else None),
                       tokenize.STRING: "string", tokenize.COMMENT: "comment",
                       tokenize.NUMBER: "number"}.get(kind)
                if tag:
                    self.editor.tag_add(tag, f"{start[0]}.{start[1]}", f"{end[0]}.{end[1]}")
        except (tokenize.TokenError, IndentationError):
            pass

    def _prefix(self):
        line = self.editor.get("insert linestart", "insert")
        return re.search(r"[A-Za-z_]\w*$", line).group(0) if re.search(r"[A-Za-z_]\w*$", line) else ""

    def suggestions(self):
        names = set(keyword.kwlist) | set(dir(builtins)) | {"self", "True", "False", "None"}
        try:
            tree = ast.parse(self.editor.get("1.0", "end-1c"))
            names |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Name))}
        except SyntaxError:
            pass
        return sorted(x for x in names if x.startswith(self._prefix()) and x != self._prefix())[:30]

    def show_completions(self):
        items = self.suggestions()
        if not items:
            return
        if self.completion_box:
            self.completion_box.destroy()
        self.completion_box = tk.Listbox(self, height=min(8, len(items)), width=28)
        for item in items:
            self.completion_box.insert("end", item)
        x = self.winfo_rootx() + 80
        y = self.winfo_rooty() + self.editor.winfo_y() + 30 + int(self.editor.index("insert").split(".")[0]) * 18
        self.completion_box.place(x=x, y=min(y, self.winfo_rooty()+self.winfo_height()-180))
        self.completion_box.focus_set()
        self.completion_box.selection_set(0)
        self.completion_box.bind("<Return>", self.accept_completion)
        self.completion_box.bind("<Escape>", lambda e: self.close_completion())

    def close_completion(self):
        if self.completion_box:
            self.completion_box.destroy()
            self.completion_box = None
        self.editor.focus_set()

    def accept_completion(self, _event=None):
        if not self.completion_box:
            return None
        value = self.completion_box.get(self.completion_box.curselection() or 0)
        self.close_completion()
        self.editor.insert("insert", value[len(self._prefix()):])
        self.highlight()
        return "break"

    def check_code(self):
        self.editor.tag_remove("error_line", "1.0", "end")
        source = self.editor.get("1.0", "end-1c")
        try:
            tree = ast.parse(source)
            hints = []
            assigned = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            suspicious = sorted((loaded - assigned - set(dir(builtins))) & {x for x in loaded if x not in {"self"}})
            if suspicious:
                hints.append("Possible undefined names: " + ", ".join(suspicious))
            for n in ast.walk(tree):
                if isinstance(n, ast.Compare) and isinstance(n.left, ast.Constant) and isinstance(n.comparators[0], ast.Constant):
                    hints.append(f"Line {n.lineno}: compare values of the same type/value; check this condition.")
            self.write_output("✓ No syntax errors found.\n" + ("Logic hints:\n- " + "\n- ".join(hints) if hints else "✓ No simple logic warnings found."), clear=True)
            self.status.config(text="Code checked successfully")
        except (SyntaxError, IndentationError) as exc:
            line = exc.lineno or 1
            self.editor.tag_add("error_line", f"{line}.0", f"{line}.end")
            self.write_output(f"Syntax issue on line {line}: {exc.msg}\nTip: fix the highlighted line, then click Check code again.", clear=True)
            self.status.config(text=f"Syntax issue on line {line}")

    def run_code(self):
        if not self.save_file():
            return
        path = self.current_file
        self.check_code()
        def worker():
            try:
                result = subprocess.run([PYTHON, path], cwd=os.path.dirname(path) or None,
                    capture_output=True, text=True, timeout=10)
                output = result.stdout + ("\nErrors:\n" + result.stderr if result.stderr else "")
                self.after(0, lambda: self.write_output(output or "Program finished with no output.", clear=True))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self.write_output("Stopped: program ran longer than 10 seconds.", clear=True))
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    PythonMentorIDE().mainloop()
