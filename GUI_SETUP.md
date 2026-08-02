# MiniLang Compiler Studio

This interface is a Python/Tkinter front end for the existing `build/mcc`
compiler. It does not duplicate compiler logic. Each Run action writes the
editor contents to a temporary `.mc` file and invokes the real executable with
`--tokens`, `--ast`, `--symtab`, or `--tac`.

## Features

- Line-numbered MiniLang editor with syntax highlighting and undo/redo
- New, open, save, and save-as source-file actions
- Valid built-in examples plus an intentional error example
- Separate Tokens, AST, Symbol Table, TAC, and Diagnostics tabs
- Full pipeline on a background thread, so the window remains responsive
- Phase status, exit codes, compiler timing, and compiler-path validation
- Headless backend self-test for WSL terminals and CI

## One-time WSL2 preparation

Run these commands from Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-tk build-essential flex bison
cd ~/Compiler-Construction-Lab-Project
make
```

If your repository has a different folder name, change only the `cd` command.
All remaining commands in this guide assume you are at the repository root.

## Manual implementation and commit sequence

The files are intentionally grouped into small tasks. Create the named files,
copy their supplied contents, run the verification command, and only then make
the shown commit. Nothing in this sequence modifies the C++ compiler.

### Task 1 — compiler adapter

Create:

```bash
mkdir -p gui
touch gui/__init__.py gui/compiler_runner.py
```

After pasting both files, verify:

```bash
python3 -m py_compile gui/__init__.py gui/compiler_runner.py
python3 -c "from pathlib import Path; from gui.compiler_runner import CompilerRunner; print(CompilerRunner(Path.cwd()).validate())"
```

The second command should print `(True, 'Compiler ready: .../build/mcc')`.
Then commit and push:

```bash
git add gui/__init__.py gui/compiler_runner.py
git commit -m "feat(gui): add compiler process adapter"
git push
```

### Task 2 — editor and examples

Create:

```bash
touch gui/code_editor.py gui/examples.py
```

After pasting both files, verify and commit:

```bash
python3 -m py_compile gui/code_editor.py gui/examples.py
git add gui/code_editor.py gui/examples.py
git commit -m "feat(gui): add MiniLang editor and examples"
git push
```

### Task 3 — application window

Create:

```bash
touch gui/app.py
```

After pasting the file, verify and commit:

```bash
python3 -m py_compile gui/app.py
python3 -c "from gui.app import MiniLangIDE; print('GUI module import: PASS')"
git add gui/app.py
git commit -m "feat(gui): add compiler studio interface"
git push
```

### Task 4 — launcher and documentation

Create:

```bash
touch run_gui.py GUI_SETUP.md
chmod +x run_gui.py
```

After pasting both files, run the complete backend test:

```bash
python3 run_gui.py --self-test
```

Expected final line:

```text
GUI backend self-test passed.
```

Now open the window:

```bash
python3 run_gui.py
```

When the window and pipeline work, commit and push:

```bash
git add run_gui.py GUI_SETUP.md
git commit -m "feat(gui): add launcher and WSL setup guide"
git push
```

## Daily use

Build the compiler after C++ changes, then launch the interface:

```bash
make
python3 run_gui.py
```

Useful shortcuts:

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New source |
| `Ctrl+O` | Open source |
| `Ctrl+S` | Save source |
| `Ctrl+Shift+S` | Save as |
| `F5` | Run the full pipeline |
| `Ctrl+1` | Run Tokens |
| `Ctrl+2` | Run AST |
| `Ctrl+3` | Run Symbol Table |
| `Ctrl+4` | Run TAC |

## Compiler-path override

The default executable is `./build/mcc`. To use another build:

```bash
python3 run_gui.py --compiler /absolute/path/to/mcc
```

Or set the project-specific environment variable for one launch:

```bash
MINILANG_COMPILER=/absolute/path/to/mcc python3 run_gui.py
```

## WSL2 display troubleshooting

On Windows 11, GUI applications normally open through WSLg. If the backend
self-test passes but no window opens:

1. Close Ubuntu.
2. In Windows PowerShell, run `wsl --update`, followed by `wsl --shutdown`.
3. Start Ubuntu again and run `python3 run_gui.py` from the repository root.

If the message says Tkinter is missing, install it with:

```bash
sudo apt install -y python3-tk
```

If the compiler badge is red, first run `make`, then click the badge to see the
exact path being checked.
