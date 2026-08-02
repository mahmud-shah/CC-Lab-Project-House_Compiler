# MiniLang Compiler — Architecture and Implementation Roadmap

**Project:** Design and Implement a Mini Programming Language Compiler Using Flex and Bison

**Course:** Compiler Construction Lab, Department of CSE, Metropolitan University

**Implementation:** C++17 compiler core with a Python 3/Tkinter desktop interface

**Primary platform:** Ubuntu/WSL2

**Document status:** As-built architecture and final verification roadmap

**Last updated:** 3 August 2026

---

## 1. Purpose and Current Status

This document describes the architecture that is actually implemented in the
MiniLang repository. It replaces the earlier pre-implementation proposal.
Planned features are not presented as completed work.

The project contains the six compiler phases required by the project manual:

1. lexical analysis;
2. syntax analysis;
3. Abstract Syntax Tree (AST) construction;
4. symbol-table management;
5. semantic analysis; and
6. Three Address Code (TAC) generation.

It also contains an optional professional Tkinter interface that operates on
the existing `build/mcc` executable. The GUI does not duplicate the compiler's
lexing, parsing, type checking, or code-generation logic.

### Verified implementation status

| Area | Status | Evidence |
|---|---|---|
| Flex lexical analyzer | Complete | `src/lexer/lexer.l`; four lexical golden tests |
| Bison syntax analyzer | Complete | `src/parser/parser.y`; conflict checks in `Makefile`; four syntax golden tests |
| AST hierarchy and printer | Complete | `include/minilang/ast.hpp`, `src/ast/`, `--ast` |
| Nested-scope symbol table | Complete | `include/minilang/symbol_table.hpp`, `src/symbol_table/`, `--symtab` |
| Semantic analyzer | Complete | `src/semantic/`; nine semantic golden tests |
| TAC generator | Complete | `src/tac/`; ten TAC golden comparisons |
| Command-line driver | Complete | `src/main.cpp`, `build/mcc` |
| Tkinter compiler studio | Complete | `run_gui.py`, `gui/` |
| Automated regression checks | Complete | 42 checks over 32 distinct `.mc` programs |

The verified command-line result is:

```text
42 passed, 0 failed
```

---

## 2. Authoritative MiniLang Specification

The project manual is the authority for the language. The compiler implements
a fixed teaching language rather than a general subset of C or C++.

### 2.1 Types

MiniLang contains exactly three base types:

| Type | Meaning |
|---|---|
| `int` | Integer value |
| `float` | Floating-point value |
| `bool` | Boolean value: `true` or `false` |

Strings, characters, arrays, functions, and user-defined types are not part of
the implemented base language.

### 2.2 Statements

The implemented statements are:

- declaration: `int x;`
- assignment: `x = 10;`
- print: `print x;`
- `if`
- `if-else`
- `while`
- nested block: `{ ... }`

Declaration and initialization are separate operations. Syntax such as
`int x = 10;` is not part of this grammar.

### 2.3 Expressions and operators

| Category | Operators |
|---|---|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Relational | `<`, `>`, `<=`, `>=` |
| Equality | `==`, `!=` |
| Logical | `&&`, `||`, `!` |
| Unary arithmetic | `-` |
| Grouping | `( expression )` |

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Integer literals contain digits;
float literals use `digits.digits`. The scanner discards whitespace, `//` line
comments, and `/* ... */` block comments.

### 2.4 Implemented type rules

| Rule | Implemented behavior |
|---|---|
| Numeric arithmetic | Operands must be `int` or `float`; mixed arithmetic produces `float` |
| Modulus | Both operands must be `int` |
| Relational operators | Both operands must be numeric; result is `bool` |
| Equality | Numeric-to-numeric or `bool`-to-`bool`; result is `bool` |
| Logical operators | Operands must be `bool` |
| Conditions | `if` and `while` conditions must be `bool` |
| Widening | Assigning `int` to `float` is allowed and emits an explicit TAC cast |
| Narrowing | Assigning `float` to `int` is rejected |
| Boolean isolation | Boolean and numeric values cannot be mixed in assignments or arithmetic |
| Shadowing | An inner scope may declare a name already used in an outer scope |
| Redeclaration | Reusing a name in the same scope is rejected |

Compile-time division-by-zero warnings and uninitialized-variable warnings are
not implemented. The symbol table records initialization state for display,
but it does not diagnose every read of an uninitialized variable.

### 2.5 Out of scope

The manual defines TAC as the final compiler output. The project does not
generate assembly, machine code, object code, or native executables from
MiniLang source. Register allocation and optimization passes are also outside
the implemented core.

---

## 3. System Architecture

The system has two layers:

1. the C++ compiler executable, which is the source of truth; and
2. the Python/Tkinter desktop interface, which invokes and presents that
   executable.

```text
MiniLang source (.mc)
        |
        v
Flex scanner -> Bison parser + AST -> Semantic analyzer + Symbol table
                                                    |
                                                    v
                                             TAC generator
                                                    |
                                                    v
                                         CLI text / .tac output

Tkinter GUI -> CompilerRunner -> build/mcc subprocesses -> structured views
```

### 3.1 Compiler dependency direction

```text
common types and diagnostics
       |
       +--> lexer (Flex)
       +--> parser (Bison) --> AST
                               |
                               +--> AST printer
                               +--> semantic analyzer --> symbol table
                               +--> TAC generator

main.cpp coordinates all compiler modules.
```

The dependency direction is intentionally one-way. The AST does not depend on
the GUI, the semantic analyzer, or TAC output. Semantic analysis and TAC
generation are independent visitors over the same AST.

### 3.2 Core technology choices

| Concern | Implemented choice | Reason |
|---|---|---|
| Compiler language | C++17 | Clear class hierarchy, RAII-friendly ownership, standard containers |
| Scanner | Flex | Required by the project manual |
| Parser | Bison C skeleton compiled as C++ | Direct integration with `%union` AST pointers and broad documentation |
| Build | GNU Make | Reproducible scanner/parser generation and C++ compilation |
| AST processing | Visitor pattern | Separate printing, semantic analysis, and TAC generation |
| Symbol table | Stack of hash maps plus archived scopes | Correct nested lookup and complete post-analysis display |
| Diagnostics | Shared collecting `ErrorReporter` | Uniform multi-error reporting with locations and hints |
| Desktop interface | Python 3 with Tkinter/ttk | Available on Ubuntu/WSL2 without third-party GUI packages |
| GUI/compiler boundary | Subprocess adapter | Keeps the interface independent of compiler internals |
| GUI concurrency | Worker threads plus a Tk event queue | Prevents compiler, build, and test operations from freezing the window |

---

## 4. Compiler Modules

### 4.1 Lexical analyzer

**Files:** `src/lexer/lexer.l`, `include/minilang/lexer.hpp`

The scanner recognizes all keywords, identifiers, integer/float/boolean
literals, operators, and delimiters. Multi-character operators are declared
before their single-character prefixes. Keyword rules precede the identifier
rule, while Flex longest-match behavior still allows names such as `integer`.

The scanner tracks the starting line and column of each token. It reports and,
where possible, continues after:

- unsupported characters;
- a single `&` or `|` instead of `&&` or `||`;
- identifiers beginning with digits;
- malformed floating-point literals; and
- unterminated block comments.

`--tokens` is a dedicated scanner mode. It prints a token table and returns
exit code 1 if lexical errors were collected.

### 4.2 Syntax analyzer

**File:** `src/parser/parser.y`

The parser builds the AST directly in Bison reduction actions. Bison location
tracking uses the project's `SourceLocation` type, so every AST node receives a
line and column.

The grammar supports declarations, assignments, control flow, print
statements, nested blocks, unary expressions, binary expressions, identifiers,
and all three literal types.

Expression precedence, from lowest to highest, is:

| Level | Operators | Associativity |
|---:|---|---|
| 1 | `||` | left |
| 2 | `&&` | left |
| 3 | `==`, `!=` | left |
| 4 | `<`, `>`, `<=`, `>=` | left |
| 5 | `+`, `-` | left |
| 6 | `*`, `/`, `%` | left |
| 7 | `!`, unary `-` | precedence-controlled unary operators |

`else` binds to the nearest unmatched `if`. Recovery productions synchronize
at `;` and `}`, allowing multiple syntax diagnostics where the remaining token
stream is recoverable. The Makefile treats shift/reduce and reduce/reduce
conflicts as build errors.

### 4.3 Abstract Syntax Tree

**Files:** `include/minilang/ast.hpp`, `src/ast/ast.cpp`,
`src/ast/ast_printer.cpp`

The implemented hierarchy contains:

- `ProgramNode`
- `BlockNode`
- `DeclarationNode`
- `AssignmentNode`
- `IfNode`
- `WhileNode`
- `PrintNode`
- `BinaryExprNode`
- `UnaryExprNode`
- `IdentifierNode`
- `IntLiteralNode`
- `FloatLiteralNode`
- `BoolLiteralNode`

Expression nodes store an inferred `Type`; assignments store the resolved
target type. Each concrete node implements `accept(ASTVisitor&)`. The AST owns
its child pointers and destroys them through virtual destructors.

### 4.4 Symbol table

**Files:** `include/minilang/symbol_table.hpp`, `src/symbol_table/`

Active scopes are represented as:

```cpp
std::vector<std::unordered_map<std::string, Symbol>>
```

Lookup walks from the innermost scope outward. Insertion checks only the
current scope, which permits legal shadowing while rejecting same-scope
redeclaration. Exited scopes are archived so `--symtab` can display symbols
from completed nested blocks.

Every `Symbol` records:

- name;
- type;
- scope level;
- declaration line; and
- initialization status.

### 4.5 Semantic analyzer

**Files:** `include/minilang/semantic_analyzer.hpp`, `src/semantic/`

The semantic analyzer is an AST visitor. It performs declaration insertion,
identifier lookup, scope entry/exit, expression type inference, assignment
compatibility checks, and condition validation.

It detects:

- undeclared variables;
- same-scope redeclaration;
- use after a declaring block has ended;
- invalid assignment and narrowing;
- invalid arithmetic operands;
- invalid modulus operands;
- invalid relational/equality operands;
- invalid logical operands; and
- non-boolean `if`/`while` conditions.

An internal error type suppresses unnecessary cascaded diagnostics. Semantic
analysis collects multiple independent errors rather than stopping after the
first one.

### 4.6 Three Address Code generator

**Files:** `include/minilang/tac.hpp`, `include/minilang/tac_generator.hpp`,
`src/tac/`

TAC generation runs only after successful parsing and semantic analysis. It
uses sequential temporary names (`t1`, `t2`, ...) and labels (`L1`, `L2`, ...).

The instruction set covers:

```text
x = y
x = y op z
x = op y
x = (float) y
ifTrue x goto L
ifFalse x goto L
goto L
L:
print x
```

The generator supports assignments, arithmetic, relational/equality
expressions, logical expressions, unary operations, `if`, `if-else`, `while`,
and `print`. Logical `&&` and `||` use short-circuit control flow. Assigning an
integer expression to a float variable emits an explicit cast.

### 4.7 Diagnostics and exit codes

All compiler phases use this form:

```text
<Category> Error [line L, col C]: <message>
  --> hint: <possible correction>
```

Categories are `Lexical`, `Syntax`, and `Semantic`.

| Exit code | Meaning |
|---:|---|
| 0 | Requested operation completed without compiler errors |
| 1 | Source contained lexical, syntax, or semantic errors |
| 2 | Command-line usage, input-file, or output-file failure |
| 124/126/127 | GUI adapter status for timeout, process-start failure, or missing compiler |

---

## 5. Command-Line Driver

**File:** `src/main.cpp`

```text
./build/mcc <source-file> [options]
```

| Option | Behavior |
|---|---|
| `--tokens` | Print token stream; this scanner-only mode takes precedence |
| `--ast` | Parse and print the AST |
| `--symtab` | Parse, analyze, and print the symbol table |
| `--tac` | Parse, analyze, and print TAC |
| `-o <file>` | Generate TAC and write it to a file |
| `--help` | Print CLI help |

With no inspection flag, the driver performs parsing and semantic analysis and
prints `Compilation successful.` for a clean source. It does not print TAC by
default. TAC is produced only by `--tac` or `-o`.

If parsing produced errors, semantic analysis is not started. If semantic
analysis fails, TAC is suppressed.

---

## 6. Desktop Interface Architecture

**Entry point:** `run_gui.py`

**Toolkit:** Python 3, Tkinter, and ttk

**Compiler dependency:** existing `build/mcc`

The final interface is a presentation layer around the command-line compiler.
It never imports C++ compiler internals or attempts to reproduce compiler
rules in Python.

### 6.1 GUI modules

| Module | Responsibility |
|---|---|
| `gui/app.py` | Window composition, commands, status, worker coordination |
| `gui/code_editor.py` | Editing, line numbers, syntax colors, indentation, search, zoom, bracket matching, diagnostics |
| `gui/compiler_runner.py` | Safe subprocess execution using temporary `.mc` files |
| `gui/diagnostics.py` | Parse, display, navigate, copy, and save compiler diagnostics |
| `gui/output_parsers.py` | Convert CLI token/AST/symbol/TAC text into structured data |
| `gui/output_views.py` | Token table, AST tree, symbol table, and TAC table |
| `gui/test_catalog.py` | Discover the 32 distinct valid/example/invalid source files |
| `gui/test_runner.py` | Cross-platform implementation of the 42 regression checks |
| `gui/test_dashboard.py` | Live progress, filtering, details, expected/actual comparison, cancellation |
| `gui/widgets.py` | Six-stage pipeline strip and reusable output view |
| `gui/theme.py` | Dark Modern palette and ttk style definitions |
| `gui/polish.py` | Code-native toolbar icons, tooltips, and activity animation |
| `gui/settings.py` | User-level window, splitter, and selected-tab persistence |
| `gui/examples.py` | Built-in fallback example source |

The sidebar contains the Test Explorer only. Normal files remain accessible
through **Open** or `Ctrl+O`. Test files are loaded as protected editor copies,
so GUI experimentation does not overwrite repository tests.

### 6.2 Six-stage visual pipeline

The GUI displays the manual's conceptual stages:

```text
Lexical -> Syntax -> AST -> Symbols -> Semantic -> TAC
```

The CLI exposes four inspection modes, so the GUI maps them as follows:

| CLI invocation | Visual stages and view |
|---|---|
| `--tokens` | Lexical; structured token table |
| `--ast` | Syntax and AST; hierarchical AST viewer |
| `--symtab` | Symbols and Semantic; scoped symbol table |
| `--tac` | TAC; structured TAC table |

The full GUI pipeline runs these modes separately against the same editor
buffer. This preserves the existing CLI and gives each view its original raw
compiler output.

### 6.3 Output workspace

The output notebook contains:

1. Compiler Output
2. Lexical Output
3. Syntax / AST
4. Semantic / Symbols
5. Three Address Code
6. Errors
7. Warnings
8. Console
9. Build Log
10. Test Suite
11. Expected Output

The compiler currently reports errors, not a separate warning class. The
Warnings view is retained for interface completeness and future compiler
extensions; it reports that no warnings were produced when appropriate.

### 6.4 Threading and process safety

Tkinter widgets are updated only on the main thread. Build, compilation, and
regression work runs in daemon worker threads. Workers place immutable results
onto a queue, and the Tk event loop polls that queue.

`CompilerRunner` invokes subprocesses with argument lists rather than shell
strings. Editor content is written to a temporary directory for each compiler
call. Standard output, standard error, exit code, and duration are captured.
Timeout and process-start failures are converted into explicit GUI results.

The regression dashboard cancellation event stops between individual compiler
checks; it does not terminate a compiler process in the middle of a check.

### 6.5 Interface behavior

The final GUI includes:

- a Dark Modern professional theme;
- code-native toolbar icons and delayed tooltips;
- a resizable Test Explorer, editor, and output area;
- hide/show controls for the explorer and output panel;
- full-screen mode;
- line/column, compiler state, timing, token, error, and warning status;
- clickable diagnostics and source-location navigation;
- raw-output copy/save actions;
- session logging;
- a responsive 42-check dashboard; and
- layout persistence outside the repository.

Tkinter does not provide Qt-style detachable dock widgets. The implemented
alternative is a resizable paned workspace with independently hideable panels.

---

## 7. Build and Execution

### 7.1 Required packages

```bash
sudo apt update
sudo apt install -y build-essential flex bison make python3 python3-tk
```

WSL2 requires WSLg or another configured graphical display for Tkinter.

### 7.2 Compiler commands

```bash
make
./build/mcc examples/sample.mc
./build/mcc examples/sample.mc --tokens
./build/mcc examples/sample.mc --ast
./build/mcc examples/sample.mc --symtab
./build/mcc examples/sample.mc --tac
./build/mcc examples/sample.mc -o output.tac
```

### 7.3 GUI commands

```bash
python3 run_gui.py --self-test
python3 run_gui.py
```

`run_gui.py --self-test` validates the compiler and exercises tokens, AST,
symbol-table, and TAC modes without opening a window.

### 7.4 Clean build and tests

```bash
make clean
make
make test
```

---

## 8. Repository Layout

```text
CC-Lab-Project-House_Compiler/
├── include/minilang/          C++ public headers
├── src/
│   ├── lexer/lexer.l          Flex specification
│   ├── parser/parser.y        Bison specification
│   ├── ast/                   AST implementation and printer
│   ├── common/                diagnostics and token names
│   ├── symbol_table/          scoped table and printer
│   ├── semantic/              semantic-analysis visitor
│   ├── tac/                   TAC model and generator
│   └── main.cpp               CLI driver
├── gui/                       Tkinter compiler studio
├── examples/sample.mc         manual-aligned example
├── tests/
│   ├── valid/                 valid sources and TAC golden files
│   └── invalid/
│       ├── lexical/           source + expected `.err`
│       ├── syntax/            source + expected `.err`
│       └── semantic/          source + expected `.err`
├── scripts/run_tests.sh       shell regression runner
├── docs/
│   ├── design/                this architecture document
│   ├── grammar/               formal grammar documentation
│   └── report/                report source
├── run_gui.py                 GUI entry point and backend self-test
├── GUI_SETUP.md               GUI installation notes
├── GUI_USER_GUIDE.md          GUI operation and demo guide
├── Makefile                   compiler build and test targets
└── README.md                  project overview and CLI instructions
```

Generated files belong under `build/` and are excluded from version control.
Python cache directories and generated `output.tac` files should also remain
untracked.

---

## 9. Regression Test Architecture

There are 32 distinct `.mc` programs. Ten TAC programs participate in two
checks: successful compilation and exact TAC comparison. Therefore, the suite
contains 42 checks rather than 42 distinct programs.

| Check category | Count |
|---|---:|
| Valid compilation (`tests/valid/*.mc` and `examples/*.mc`) | 15 |
| Lexical diagnostic golden files | 4 |
| Syntax diagnostic golden files | 4 |
| Semantic diagnostic golden files | 9 |
| TAC golden-output comparisons | 10 |
| **Total** | **42** |

Invalid tests require exit code 1 and an exact standard-error match against
their `.err` file. TAC checks compare standard output with the corresponding
`.tac` file. The Python GUI runner additionally requires the expected exit
code and normalizes line endings for cross-platform execution.

The shell script should continue to be maintained so its TAC section also
explicitly requires exit code 0 and empty standard error, matching the stricter
GUI runner.

### Verification commands

```bash
python3 -m compileall -q gui run_gui.py
make
python3 run_gui.py --self-test
./scripts/run_tests.sh
git status --short
```

Expected results:

- GUI backend modes all print `PASS`;
- regression result is `42 passed, 0 failed`; and
- `git status --short` is empty after generated caches/output are removed.

---

## 10. Completed Implementation Roadmap

| Milestone | Delivered artifacts | Status |
|---|---|---|
| Architecture and requirements | grammar, type rules, module boundaries | Complete |
| Build scaffolding | Makefile, include/src layout, generated-file rules | Complete |
| Lexer | tokens, comments, locations, lexical recovery | Complete |
| Parser and AST | grammar, precedence, recovery, node hierarchy, printer | Complete |
| Symbol table | nested scopes, shadowing, archived scope output | Complete |
| Semantic analysis | type/scope rules and multi-error collection | Complete |
| TAC generation | expressions, control flow, short-circuit logic, casts | Complete |
| Regression suite | 42 automated checks and golden files | Complete |
| Professional GUI | editor, diagnostics, structured views, tests, persistence | Complete |
| GUI documentation | setup and user/demo guides | Complete |

The compiler and GUI implementation roadmap is complete. Remaining work is
submission preparation rather than compiler architecture.

---

## 11. Requirement Traceability

| Manual requirement | Implementation | Verification |
|---|---|---|
| Lexical analysis in Flex | `src/lexer/lexer.l` | token mode + 4 lexical golden tests |
| Complete Bison CFG | `src/parser/parser.y` | Makefile conflict errors + 4 syntax tests |
| AST construction and printing | `include/minilang/ast.hpp`, `src/ast/` | `--ast` and valid examples |
| Nested-scope symbol table | `src/symbol_table/` | `--symtab`, nested-scope valid test |
| Required semantic errors | `src/semantic/` | 9 semantic golden tests |
| TAC for expressions/control flow/print | `src/tac/` | 10 exact TAC golden checks |
| Valid manual-style example | `examples/sample.mc` | valid compilation and GUI self-test |
| Build system | `Makefile` | clean Flex/Bison/C++17 build |
| Valid and invalid tests | `tests/`, `scripts/run_tests.sh` | 42 checks |
| Optional GUI | `run_gui.py`, `gui/` | backend self-test and GUI dashboard |

GitHub participation, report naming, presentation slides, screenshots, and
individual viva readiness are submission-process requirements. They must be
verified from the final repository and team records; they cannot be proven by
compiler source code alone.

---

## 12. Final Architectural Conclusion

MiniLang is implemented as a layered compiler front-end with a single AST,
visitor-based analysis, nested scopes, collected diagnostics, and structured
TAC generation. The C++ executable remains the authoritative compiler. The
Tkinter application is a separate, responsive presentation layer that invokes
the executable safely and exposes each compiler result in a demonstrable IDE
workspace.