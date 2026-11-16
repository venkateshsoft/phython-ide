# Python Mentor IDE

A small beginner-friendly Python editor with no third-party packages:

- live syntax coloring
- Ctrl+Space / automatic completion for keywords, built-ins, and names in the file
- syntax checking with a highlighted error line
- a few explainable logic hints
- save, open, run, and a 10-second safety timeout

Run it with:

```powershell
& "C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe" .\python_mentor_ide.py
```

If Tk/IDLE is unavailable, use the browser version instead:

```powershell
& "C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe" .\mentor_web_ide.py
```

Then open http://127.0.0.1:8765 in a browser.

The browser IDE includes an **Auto-fix intent** action. It recognizes common beginner keywords such as duplicate, factorial, Fibonacci, prime, palindrome, reverse, even/odd, sum, and total, then generates executable logic while preserving literal data found in the editor. Pressing **Run** applies that safe correction first, then executes the corrected code. It also repairs common missing-colon syntax errors and smart quotes. The **Clear** button resets the editor and feedback panel.

This is a rule-based mentor engine, not a general-purpose AI programmer: when intent is ambiguous, it refuses to guess and explains why.

The editor can catch syntax errors and common beginner mistakes. Logic is intent-dependent, so the IDE reports suggestions rather than silently changing code that might be correct for the user's goal.
