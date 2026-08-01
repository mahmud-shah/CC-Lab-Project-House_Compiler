# MiniLang Compiler

A complete compiler front-end for a custom programming language called
**MiniLang**, built using **Flex**, **Bison**, and **C++17** as part of the
Compiler Construction Lab project.

**Course:** Compiler Construction Lab
**Institution:** Department of Computer Science and Engineering, Metropolitan University, Bangladesh
**Developer:** Al Mahmud

---

## Table of Contents

- [Project Overview](#project-overview)
- [Language Summary](#language-summary)
- [Compiler Pipeline](#compiler-pipeline)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Build Instructions](#build-instructions)
- [Usage and Execution](#usage-and-execution)
- [Compiler Phases](#compiler-phases)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Examples](#examples)
- [Limitations](#limitations)
- [Future Work](#future-work)

---

## Project Overview

This project implements a complete compiler front-end with intermediate code
generation for a custom mini programming language. The compiler reads source
files and passes them through six integrated phases:

1. **Lexical Analysis** — tokenises the source using Flex
2. **Syntax Analysis** — parses tokens using a Bison grammar
3. **AST Construction** — builds an Abstract Syntax Tree during parsing
4. **Symbol Table** — tracks all declared identifiers and their scopes
5. **Semantic Analysis** — enforces all type and scope rules
6. **TAC Generation** — produces Three Address Code intermediate output

---

## Language Summary

MiniLang supports three data types and six categories of statements.

### Data Types

| Type | Description |
|---|---|
| `int` | Signed integer |
| `float` | Floating-point number |
| `bool` | Boolean (`true` / `false`) |

### Statements

```
int x;              // variable declaration
x = 5;              // assignment
print x;            // print
if (x > 0) { }     // if
if (x > 0) { }     // if-else
else { }
while (x > 0) { }  // while loop
{ }                 // nested block (creates new scope)
```

### Operators

| Category | Operators |
|---|---|
| Arithmetic | `+` `-` `*` `/` `%` |
| Relational | `<` `>` `<=` `>=` `==` `!=` |
| Logical | `&&` `\|\|` `!` |

### Sample Program

```
int x;
int y;
bool flag;
x = 10;
y = 0;
flag = true;
while (x > 0) {
    y = y + x;
    x = x - 1;
}
if (flag == true) {
    print y;
} else {
    print x;
}
```

---

## Compiler Pipeline

```
Source Code (.mc)
      |
      v
+------------------+
|  Lexical Analyzer | (Flex)
|  lexer.l         |
+------------------+
      | Token Stream
      v
+------------------+
|  Syntax Analyzer | (Bison)
|  parser.y        |
+------------------+
      | Abstract Syntax Tree
      v
+------------------+
|  Semantic        | (Visitor Pattern)
|  Analyzer        |----> Symbol Table
|  + Type Checker  |
+------------------+
      | Annotated AST
      v
+------------------+
|  TAC Generator   | (Visitor Pattern)
+------------------+
      | Three Address Code
      v
   Output (.tac)
```

---

## Project Structure

```
CC-Lab-Project-House_Compiler/
├── docs/
│   ├── design/              Architecture and design decisions
│   ├── grammar/             Formal CFG specification
│   └── viva/                Viva preparation notes
├── include/
│   └── minilang/            All public header files
│       ├── ast.hpp          AST node hierarchy
│       ├── ast_printer.hpp  AST text printer
│       ├── error_reporter.hpp Diagnostic collector
│       ├── lexer.hpp        Lexer interface
│       ├── semantic_analyzer.hpp
│       ├── source_location.hpp
│       ├── symbol_table.hpp
│       ├── symbol_table_printer.hpp
│       ├── tac.hpp          TAC instruction set
│       ├── tac_generator.hpp
│       └── type.hpp         Type system
├── src/
│   ├── ast/                 AST node implementations
│   ├── common/              Shared utilities (ErrorReporter, token names)
│   ├── lexer/               lexer.l (Flex specification)
│   ├── parser/              parser.y (Bison grammar)
│   ├── semantic/            Semantic analyzer visitor
│   ├── symbol_table/        Symbol table and printer
│   ├── tac/                 TAC generator and printer
│   └── main.cpp             Compiler driver / CLI
├── examples/                Representative sample programs
├── tests/
│   ├── valid/               Valid programs with golden TAC outputs
│   ├── invalid/
│   │   ├── lexical/         Lexical error programs
│   │   ├── syntax/          Syntax error programs
│   │   └── semantic/        Semantic error programs
│   └── README.md            Test suite documentation
├── scripts/
│   └── run_tests.sh         Regression test runner
├── Makefile                 Build system
├── .gitignore
└── README.md
```

---

## Technology Stack

| Tool | Purpose |
|---|---|
| Linux (Ubuntu 24.04) | Development and build environment |
| Flex 2.6.4 | Lexical analyzer generator |
| Bison 3.8.2 | Parser generator |
| g++ (GCC, C++17) | Compiler for generated and hand-written code |
| GNU Make | Build automation |
| Git / GitHub | Version control |

---

## Build Instructions

### Prerequisites

Install the required tools on Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y build-essential flex bison git make
```

Verify installation:

```bash
g++ --version
flex --version
bison --version
make --version
```

### Build

Clone the repository and build with a single command:

```bash
git clone git@github.com:YOUR-USERNAME/CC-Lab-Project-House_Compiler.git
cd CC-Lab-Project-House_Compiler
make
```

Expected output:

```
bison ...
g++ ... src/main.cpp ...
...
Built build/mcc
```

The compiler binary is produced at `build/mcc`.

### Clean

```bash
make clean
```

### Run Tests

```bash
make test
```

Expected output:

```
PASS  valid    tests/valid/tac_complete.mc
PASS  valid    examples/sample.mc
...
42 passed, 0 failed
```

---

## Usage and Execution

### Basic syntax

```bash
./build/mcc <source-file> [options]
```

### Options

| Option | Description |
|---|---|
| `--tokens` | Print the token stream produced by the lexer |
| `--ast` | Print the Abstract Syntax Tree after parsing |
| `--symtab` | Print the symbol table after semantic analysis |
| `--tac` | Print Three Address Code to stdout |
| `-o <file>` | Write TAC to a file |
| `--help` | Show usage information |

### Execution Examples

**Full pipeline — compile a source file:**

```bash
./build/mcc examples/sample.mc
```

Output:
```
Compilation successful.
```

**Dump the token stream:**

```bash
./build/mcc examples/sample.mc --tokens
```

Output:
```
LOC       TOKEN           LEXEME          VALUE
----------------------------------------------------
2:1       KEYWORD_INT     int
2:5       IDENTIFIER      x               "x"
2:6       SEMICOLON       ;
...
```

**Print the Abstract Syntax Tree:**

```bash
./build/mcc examples/sample.mc --ast
```

Output:
```
Program  [1:1]
  Declaration 'x' : int  [2:5]
  Declaration 'y' : int  [3:5]
  Declaration 'flag' : bool  [4:6]
  Assignment 'x'  [6:1]
    IntLiteral 10  [6:5]
  ...
```

**Print the symbol table:**

```bash
./build/mcc examples/sample.mc --symtab
```

Output:
```
=== Symbol Table ===

Scope Level 0 (global)
--------------------------------------------------
NAME        TYPE    SCOPE  LINE  INITIALIZED
x           int     0      2     yes
y           int     0      3     yes
flag        bool    0      4     yes
```

**Generate Three Address Code:**

```bash
./build/mcc examples/sample.mc --tac
```

Output:
```
; === Three Address Code: examples/sample.mc ===

    x = 10
    y = 0
    flag = true
L1:
    t1 = x > 0
    ifFalse t1 goto L2
    t2 = y + x
    y = t2
    t3 = x - 1
    x = t3
    goto L1
L2:
    t4 = flag == true
    ifFalse t4 goto L3
    print y
    goto L4
L3:
    print x
L4:
```

**Write TAC to a file:**

```bash
./build/mcc examples/sample.mc -o output.tac
cat output.tac
```

---

## Compiler Phases

### Phase 1 — Lexical Analyzer (`src/lexer/lexer.l`)

The Flex-based scanner reads the source character by character and groups
characters into tokens. It tracks line and column numbers for every token
so all error messages can point to the exact position in the source.

Supported token classes:
- **Keywords:** `int` `float` `bool` `if` `else` `while` `print` `true` `false`
- **Identifiers:** `[A-Za-z_][A-Za-z0-9_]*`
- **Integer literals:** `[0-9]+`
- **Float literals:** `[0-9]+.[0-9]+`
- **All 15 operators** including multi-character tokens (`<=`, `>=`, `==`, `!=`, `&&`, `||`)
- **Delimiters:** `{ } ( ) ;`
- **Comments:** `//` line comments and `/* */` block comments are discarded
- **Invalid tokens** are reported with line and column and scanning continues

### Phase 2 — Syntax Analyzer (`src/parser/parser.y`)

The Bison-based parser implements a complete, unambiguous context-free grammar
for MiniLang. Operator precedence and associativity are declared explicitly,
producing zero shift/reduce and zero reduce/reduce conflicts.

Key design decisions:
- **Dangling else** resolved by `%precedence` declarations (else binds to nearest if)
- **Error recovery** at `;` and `}` so one syntax error never hides the rest of the file

### Phase 3 — Abstract Syntax Tree (`src/ast/`)

The AST is built bottom-up during parsing. Each node represents exactly one
language construct:

`ProgramNode` → `BlockNode` → `DeclarationNode` `AssignmentNode` `IfNode`
`WhileNode` `PrintNode` → `BinaryExprNode` `UnaryExprNode` → `IntLiteralNode`
`FloatLiteralNode` `BoolLiteralNode` `IdentifierNode`

Three independent visitors walk the same tree: `ASTPrinter`,
`SemanticAnalyzer`, and `TACGenerator`.

### Phase 4 — Symbol Table (`src/symbol_table/`)

Implemented as a stack of hash maps — one map per active scope.
`enterScope()` pushes a new map; `exitScope()` pops and archives it.
Lookup walks the stack from innermost to outermost scope so inner
declarations correctly shadow outer ones.

Each symbol stores: name, type, scope level, declared line, initialized flag.

### Phase 5 — Semantic Analyzer (`src/semantic/`)

The semantic analyzer walks the annotated AST and enforces all rules the
grammar cannot check. It reports every error in the file without stopping
at the first one.

| Error Class | Example |
|---|---|
| Undeclared variable | Using `x` before `int x;` |
| Redeclaration | `int x; int x;` in the same scope |
| Scope violation | Using a variable after its block closes |
| Type mismatch | `bool b = 5;` |
| Invalid assignment | `int x = 3.14;` |
| Invalid expression | `true + 1` or `1 && 2` |
| Invalid condition | `if (x)` where `x` is `int` |

### Phase 6 — TAC Generator (`src/tac/`)

Generates Three Address Code by visiting the type-annotated AST. Each
instruction has at most three operands. Temporary variables (`t1`, `t2`, ...)
and labels (`L1`, `L2`, ...) are allocated sequentially.

Special handling:
- `&&` and `||` use **short-circuit jump chains** — the right operand is
  skipped when the left operand determines the result
- `int` assigned to a `float` variable emits an explicit `(float)` cast
- Declarations produce no TAC — variables are handled by the back-end

---

## Error Handling

All three error categories produce messages in a uniform format:

```
<Category> Error [line L, col C]: <what happened>
  --> hint: <possible fix>
```

### Lexical error example

```
Lexical Error [line 3, col 1]: Invalid token '@'
  --> hint: this character is not part of the MiniLang alphabet
```

### Syntax error example

```
Syntax Error [line 2, col 1]: Unexpected identifier, expecting ';'
  --> hint: a semicolon may be missing at the end of the previous statement
```

### Semantic error example

```
Semantic Error [line 3, col 7]: Undeclared variable 'y'
  --> hint: declare it before use, e.g. 'int y;'
```

---

## Testing

The test suite contains **42 test programs** covering every requirement
from Project Manual §15.

```bash
make test
```

| Category | Count | What is tested |
|---|---|---|
| Valid programs | 14 | Full pipeline to TAC, all language features |
| Lexical errors | 4 | Invalid tokens, malformed numbers, unterminated comment |
| Syntax errors | 4 | Missing semicolon, unbalanced parenthesis, stray else, multiple errors |
| Semantic errors | 9 | One test per error class, plus multi-error recovery |
| **Total** | **42** | |

Every invalid test is paired with a golden `.err` file.
Every TAC test is paired with a golden `.tac` file.
The runner diffs actual output against golden files and prints `PASS`/`FAIL`.

See `tests/README.md` for the full test catalogue.

---

## Examples

The `examples/` directory contains representative programs:

| File | Demonstrates |
|---|---|
| `sample.mc` | All statement types, while loop, if-else (Project Manual §5.5) |

Run any example through the full pipeline:

```bash
./build/mcc examples/sample.mc --tac
```

---

## Limitations

- TAC is the final output. No assembly, machine code, or executable is generated
  (explicitly out of scope per Project Manual §6).
- No function definitions, arrays, or for/do-while loops in the base language
  (these are optional bonus features per §14).
- Integer division truncates toward zero (standard C semantics).
- The `%` operator requires both operands to be `int`.

---

## Future Work

Optional bonus features from Project Manual §14 that can be added after the
mandatory requirements are complete:

- Arrays
- Functions with parameters and return statements
- `for` loop and `do-while` loop
- `switch-case`
- Unary increment/decrement operators (`++` `--`)
- Constant folding optimization
- Dead code elimination
- AST visualization with Graphviz
