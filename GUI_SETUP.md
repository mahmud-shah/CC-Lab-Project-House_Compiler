# MiniLang Compiler Studio

MiniLang Compiler Studio is the Tkinter desktop interface for the existing
Flex/Bison `mcc` compiler. The interface never reimplements compiler logic: all
tokens, diagnostics, AST nodes, symbols, and three-address code come directly
from `build/mcc`.

## Requirements

On Ubuntu or WSL2:

```bash
sudo apt update
sudo apt install -y python3 python3-tk make gcc flex bison
```

WSL2 users need WSLg or another configured graphical display.

## Build and launch

From the repository root:

```bash
make
python3 run_gui.py --self-test
python3 run_gui.py
```

No third-party Python package is required.

## Workspace

- **Project** lists editable repository source and documentation files.
- **Tests** groups all valid examples and invalid lexical, syntax, and semantic
  cases from the repository.
- Double-click a Project file to edit it normally.
- Double-click a Test to load a protected editor copy, preserving the original
  test and golden output.
- Drag the panel separators to resize the explorer, editor, and output areas.
- Use `Ctrl+Shift+E` and `Ctrl+J` to show or hide the explorer and output panel.

## Compiler views

The pipeline strip represents the required phases:

```text
Lexical -> Syntax -> AST -> Symbols -> Semantic -> TAC
```

The output notebook contains:

- Compiler Output
- Lexical Output
- Syntax / AST
- Semantic / Symbols
- Three Address Code
- Errors
- Warnings
- Console
- Build Log
- Test Suite
- Expected Output

Structured rows retain access to the exact raw compiler output. Source-aware
rows and diagnostics can navigate back to the corresponding editor location.

## Regression suite

Press `Ctrl+T` or choose **Run 42 Tests**. The dashboard performs the same
categories as `scripts/run_tests.sh`:

- 15 valid program checks
- 17 invalid diagnostic golden checks
- 10 TAC golden-output checks

A correct repository shows 42 passed and 0 failed. Select a result to compare
expected and actual output, or double-click it to load its source. **Stop**
requests cancellation between compiler checks.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New source buffer |
| `Ctrl+O` | Open a file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save as |
| `F5` | Run the full pipeline |
| `Ctrl+B` | Build the compiler |
| `Ctrl+T` | Run all regression checks |
| `Ctrl+1` | Lexical analysis |
| `Ctrl+2` | Syntax and AST |
| `Ctrl+3` | Semantic analysis and symbols |
| `Ctrl+4` | Three-address code |
| `Ctrl+F` | Find |
| `Ctrl+H` | Replace |
| `Ctrl+G` | Go to line |
| `Ctrl++` / `Ctrl+-` | Editor zoom |
| `Ctrl+0` | Reset editor zoom |
| `Ctrl+Shift+E` | Toggle explorer |
| `Ctrl+J` | Toggle output panel |
| `F11` | Toggle full screen |
| `Escape` | Leave full screen |

## Recommended demonstration

1. Launch the IDE and show the Project and Tests explorers.
2. Load the complete valid example and press `F5`.
3. Show all six pipeline stages passing.
4. Demonstrate the lexical table, AST hierarchy, symbol scopes, and TAC table.
5. Load `multiple_errors.mc`, compile it, and use the Errors view to navigate
   between marked source locations.
6. Press `Ctrl+T` and show all 42 regression checks passing.
7. Select one invalid test and one TAC test to demonstrate exact golden-output
   comparison.

## Architecture

- `gui/app.py` coordinates application state and background workers.
- `gui/code_editor.py` owns editing, highlighting, navigation, and diagnostics.
- `gui/compiler_runner.py` safely invokes `build/mcc` without shell expansion.
- `gui/output_parsers.py` and `gui/output_views.py` provide structured views.
- `gui/test_runner.py` and `gui/test_dashboard.py` implement regression checks.
- `gui/project_explorer.py` provides repository navigation.
- `gui/theme.py`, `gui/widgets.py`, and `gui/polish.py` provide the visual system.
- `gui/settings.py` persists window and panel layout outside the repository.

This separation keeps the GUI independent from the Flex/Bison implementation
and makes the interface safe to extend without changing compiler behavior.
