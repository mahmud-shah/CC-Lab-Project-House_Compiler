# MiniLang Compiler — Architecture & Implementation Roadmap

**Project:** Design and Implement a Mini Programming Language Compiler using Flex and Bison
**Course:** Compiler Construction Lab, Dept. of CSE, Metropolitan University
**Deadline:** 31 July (strict) · **Weight:** 40% of lab course
**Status of this document:** Phase 0 deliverable — architecture to be finalized before any code is written.

---

## 1. Project Manual Analysis (Source 1 — highest authority)

### 1.1 Requirement extraction, weighted by rubric

| # | Requirement (Manual §) | Rubric weight | Risk | Notes |
|---|---|---|---|---|
| R1 | Lexical analyzer in Flex (§4.1) | 10% | Low | Keywords, identifiers, int/float/bool literals, operators, delimiters, comments discarded, whitespace discarded, invalid tokens reported with line number |
| R2 | Parser in Bison with complete unambiguous CFG (§4.2) | 15% | Medium | Syntax errors with line numbers, error recovery via `error` token, dangling-else must be resolved deliberately |
| R3 | AST construction + printable (§4.3) | 10% | Low | Text-indented printing required; Graphviz is bonus |
| R4 | Symbol table with **nested scopes** (§4.4) | 10% | Medium | Fields: name, type, scope, line declared. Block-scoped visibility |
| R5 | Semantic analysis — 6 error classes (§4.5) | **20%** | **High** | Undeclared, redeclaration, scope violation, type mismatch, invalid assignment, invalid expression. Highest-weight single item |
| R6 | TAC generation (§4.6) | 15% | Medium | Arithmetic w/ precedence, relational, logical, `if`/`if-else`/`while` with labels & jumps, `print` |
| R7 | Documentation: README + 14-chapter report (§11–12) | 10% | Low | Report chapter structure is fixed by §12 |
| R8 | Presentation + live demo (§13) | 10% | Low | Live demo of valid + invalid programs, all three error classes, TAC output |
| R9 | Individual viva | Pass/fail gate | **High** | Can scale *all* other marks per student — viva prep material is not optional polish, it is risk insurance |
| R10 | GitHub: shared repo, all members commit, regular meaningful commits (§9) | Assessed directly | Medium | Single last-minute commit is penalized even if code works |
| R11 | Tests: valid + one per error class, paired with expected output (§15) | Feeds R1–R6 | Low | Expected/actual output pairs required |

### 1.2 Authoritative language specification (§5)

- **Types:** `int`, `float`, `bool` — exactly three, no strings, no arrays (arrays are bonus).
- **Statements:** declaration, assignment, `if`, `if-else`, `while`, `print`, nested `{ }` blocks with proper scoping.
- **Operators:** arithmetic `+ - * / %`, relational `< > <= >= == !=`, logical `&& || !`.
- **Lexical:** identifiers `[A-Za-z_][A-Za-z0-9_]*`, integer literals, float literals (e.g. `3.14`), `true`/`false`, `;` terminators, `{ } ( )`.
- **Explicitly out of scope (§6):** assembly, machine code, register allocation, optimization (beyond bonus), backends. TAC is the final output.
- **Fixed language:** we may not alter the core grammar. Differentiation happens only through §14 bonus features.

### 1.3 Ambiguities in the manual that we must resolve and document

The manual leaves the following underspecified. Each becomes a documented design decision (Section 3), which is exactly the kind of thing the viva probes.

| # | Ambiguity | Our resolution (proposed) |
|---|---|---|
| A1 | Is `int → float` implicit widening allowed (`float f; f = 3;`)? | **Allow widening** int→float in assignment and mixed arithmetic (`int + float → float`); TAC emits explicit `t = (float) x` cast instruction. Narrowing `int = float` is an error. All bool↔numeric mixing is an error (confirmed by template test `x = ready;` → error). |
| A2 | `%` on floats? | **Error.** `%` requires two `int` operands (matches C semantics, easy to defend). |
| A3 | Operands of `== !=` | Both numeric (with widening) **or** both bool. `bool == int` is an error. |
| A4 | Operands of `< > <= >=` | Numeric only. Comparing bools is an error. |
| A5 | Operands of `&& || !` | `bool` only. `1 && 2` is an "invalid expression" error (manual §4.5 explicitly lists "applying logical operators to numeric operands"). |
| A6 | `if`/`while` condition type | Must be `bool`. `if (x)` where `x` is `int` is an error. |
| A7 | Dangling else | Resolved the standard way: `else` binds to nearest `if`. Documented + handled in grammar without conflicts. |
| A8 | Division by zero constant | Semantic **warning**, not error (runtime concern; we're a front-end). |
| A9 | Use of declared-but-uninitialized variable | **Warning** (bonus polish, not required). |
| A10 | Source file extension | `.mc` (per manual pipeline diagram: "Source Code (.txt / .mc)"); compiler accepts any path. |
| A11 | Does a lexical/syntax error stop later phases? | Lexer reports and continues scanning. Parser recovers at `;` and `}`. Semantic analysis runs only if parse produced a usable AST; semantic analyzer **never stops at the first error** (collects all). TAC is generated only for fully clean programs. |

---

## 2. Reference Repository Analysis (Source 2)

Repo: `KhalidBinSelim/Compiler-Construction-Lab-Project` (26 commits, MIT, template released Jul 2026).

### 2.1 What it actually is

An **instruction/template repository — it contains no compiler implementation at all.** Contents: README (workflow: fork → rename `CC-Lab-Project-GroupXX` → add collaborators → keep public), FAQ (39 Q&A), INSTALL.md (apt packages), CHANGELOG, LICENSE, `.gitignore`, and `tests/` + `examples/` holding sample programs *as Markdown files*.

Consequence: there is no code to study, copy, or improve. "Originality" is trivially satisfied; the repo's value is as a **requirements oracle**.

### 2.2 What we extract from it (signals, not code)

1. **Error-message conventions the instructor expects** — the invalid-test files carry expected outputs in this style:
   - `Lexical Error: Invalid token '@'`
   - `Syntax Error: Missing ';' / Missing ')'`
   - `Semantic Error: Undeclared variable 'y'`, `Redeclaration of variable 'count'`, `Variable 'y' is out of scope`, `Cannot assign bool to int`, `Type mismatch in assignment — Expected bool, Found int`
   Our diagnostics will be a strict superset: same category labels, plus line:column, offending token, and a suggested fix.
2. **Semantic ground truth:** `x = ready;` (int = bool) is an error; `flag = 10 + 20;` (bool = int) is an error → confirms strict bool isolation (decision A1/A5).
3. **Test taxonomy:** valid = {declaration, assignment, arithmetic, if_else, while, complete_program}; invalid = {lexical_error, syntax_error, undeclared_variable, redeclaration, scope_violation, type_mismatch, invalid_assignment}. We adopt this as the minimum and extend it.
4. **`.gitignore`** covering `lex.yy.c`, `parser.tab.*`, objects, executables — we adopt an equivalent.
5. **Commit-message style guide** ("Add scope handling to symbol table", not "update").

### 2.3 Weaknesses in the template we will fix in our repo

| Weakness | Our improvement |
|---|---|
| Tests stored as `.md` prose, not runnable | Real `.mc` source files + `expected/` outputs + a `scripts/run_tests.sh` regression runner producing a pass/fail summary |
| No expected **TAC** outputs anywhere | Golden TAC files for every valid test |
| No Makefile, no `src/`, no `include/`, empty `docs/` | Full build system, layered source tree, complete report in `docs/` |
| Expected outputs lack line/column info | Diagnostics carry `line:col`, offending lexeme, explanation, fix hint |
| Only one semantic error per file | Also multi-error files proving the analyzer doesn't stop at the first error |
| Suggested structure lacks `tac/` and `common/` dirs | Added (the manual's own §8 tree omits TAC — an internal inconsistency we resolve in the manual's favor by adding it) |

---

## 3. Architecture

### 3.1 Technology decisions (each viva-defensible)

| Decision | Choice | Rationale | Rejected alternative |
|---|---|---|---|
| Host language | **C++17**, compiled with g++ | Real class hierarchy for AST, `std::unordered_map` scopes, RAII, `std::variant`-free simplicity | Plain C (verbose manual OO); Bison C++ skeleton `lalr1.cc` (elegant but harder to explain in viva, less documentation) |
| Flex/Bison interface | Bison **C skeleton** + `%union` of node pointers, compiled as C++ | The canonical, best-documented approach; every teammate can trace `yylex → yyparse → $$ = new Node(...)` | `api.value.type variant` (needs C++ skeleton) |
| Location tracking | Flex rule-level `line/col` counters + Bison `%locations` (`@$`) | Every token and node carries `{line, col}`; powers all diagnostics | Manual global line only (no columns) |
| AST traversal | **Visitor pattern** (`ASTVisitor` interface; `ASTPrinter`, `SemanticAnalyzer`, `TACGenerator` are visitors) | One tree, three independent consumers; adding a Graphviz printer (bonus) is one new class, zero AST changes | `switch` on node-kind enums (scatters logic) |
| Symbol table | **Stack of hash-map scopes** + retained scope snapshots for the `--symtab` dump | O(1) avg insert/lookup-current; lookup walks stack top→bottom (innermost wins); retention lets us print the full table after analysis | Single flat table with name mangling |
| Semantic errors | `ErrorReporter` collects into a list; analysis always completes | Manual: "never stop after the first semantic error" | abort-on-first |
| TAC form | Instruction list of quads, pretty-printed; `t1..tn` temps, `L1..Ln` labels | Matches manual's illustrative output exactly; quads make bonus constant-folding trivial | Expression-tree stringification |
| Boolean codegen | **Short-circuit jumping code** for `&& || !` in conditions; materialization (`t = 1/0` via labels) when a bool value is stored | Demonstrates the classic backpatch-style technique; strong viva material | Eager evaluation (wrong semantics for `&&`) |
| Driver | Single binary `mcc` with flags `--tokens --ast --symtab --tac -o <file>` | One demo command per compiler phase — maps 1:1 to the presentation checklist | Separate binaries per phase |

### 3.2 Pipeline and module dependency graph

```
 source.mc
    │
    ▼
 ┌─────────┐ tokens  ┌─────────┐  AST   ┌────────────────┐ annotated ┌────────────┐
 │  Lexer  │────────▶│ Parser  │───────▶│ SemanticAnalyzer│──────────▶│ TACGenerator│
 │ (Flex)  │         │ (Bison) │        │  + SymbolTable  │   AST     │            │
 └─────────┘         └─────────┘        └────────────────┘           └────────────┘
      │                   │                     │                          │
      └────────── ErrorReporter ◀───────────────┘                          ▼
                (shared, collects all)                                  TAC text
```

Module layering (arrows = "depends on"; no cycles):

```
common (SourceLocation, Type, ErrorReporter)
   ▲            ▲              ▲
 lexer ──▶ parser ──▶ ast ◀── semantic ◀── driver
                        ▲        │
                        │        ▼
                       tac   symbol_table
```

`common/` is dependency-free; `ast/` depends only on `common/`; `semantic/` and `tac/` depend on `ast/` + `common/`; `symbol_table/` on `common/`; the driver (`main.cpp`) wires everything.

### 3.3 Repository layout (final)

```
CC-Lab-Project-GroupXX/
├── docs/
│   ├── report/                  # LaTeX or Markdown report source + PDF (14 chapters, §12)
│   ├── grammar.md               # Formal CFG + precedence table
│   ├── design/                  # This document, diagrams
│   └── viva/                    # Per-phase viva Q&A packs
├── include/minilang/            # Public headers (one per module)
├── src/
│   ├── lexer/lexer.l
│   ├── parser/parser.y
│   ├── ast/                     # ast.hpp impl, ast_printer.cpp
│   ├── symbol_table/
│   ├── semantic/
│   ├── tac/
│   ├── common/                  # source_location, type, error_reporter, token names
│   └── main.cpp                 # driver / CLI
├── examples/                    # 4–5 showcase programs (.mc)
├── tests/
│   ├── valid/        *.mc  + expected/*.tac, *.ast, *.symtab
│   └── invalid/
│       ├── lexical/  syntax/  semantic/     (*.mc + expected/*.err)
├── scripts/run_tests.sh         # regression runner, prints PASS/FAIL matrix
├── Makefile                     # make, make test, make clean
├── .gitignore
└── README.md
```

(§8's suggested tree lacks `tac/`, `include/`, `scripts/` — the FAQ explicitly permits reorganizing "if clean and professional".)

### 3.4 Formal grammar (draft CFG — to be frozen in Phase 2)

Terminals in caps; `ε` = empty.

```
program        → stmt_list
stmt_list      → stmt_list stmt | ε
stmt           → declaration | assignment | if_stmt | while_stmt
               | print_stmt | block
declaration    → type IDENT ';'
type           → INT | FLOAT | BOOL
assignment     → IDENT '=' expr ';'
if_stmt        → IF '(' expr ')' stmt
               | IF '(' expr ')' stmt ELSE stmt
while_stmt     → WHILE '(' expr ')' stmt
print_stmt     → PRINT expr ';'
block          → '{' stmt_list '}'

expr           → expr '||' expr | expr '&&' expr
               | expr EQ expr  | expr NEQ expr
               | expr '<' expr | expr '>' expr | expr LE expr | expr GE expr
               | expr '+' expr | expr '-' expr
               | expr '*' expr | expr '/' expr | expr '%' expr
               | '!' expr | '-' expr            /* unary */
               | '(' expr ')'
               | IDENT | INT_LIT | FLOAT_LIT | TRUE | FALSE
```

Ambiguity is resolved not by rewriting into 8 precedence levels of nonterminals but by **Bison precedence declarations** (cleaner grammar, standard practice — a deliberate, defensible choice):

| Level (low→high) | Operators | Associativity |
|---|---|---|
| 1 | `\|\|` | left |
| 2 | `&&` | left |
| 3 | `==` `!=` | left |
| 4 | `<` `>` `<=` `>=` | left |
| 5 | `+` `-` | left |
| 6 | `*` `/` `%` | left |
| 7 | `!`, unary `-` | right (`%prec UMINUS`) |

Dangling else: `%precedence` on `ELSE` > unmatched `if` (or the classic "no conflict after precedence declaration" approach). Target: **0 shift/reduce, 0 reduce/reduce conflicts**, verified via `bison -Wcounterexamples --report=all`.

Error recovery productions: `stmt → error ';'` and `block → '{' error '}'` — resynchronize at statement boundaries so one syntax error doesn't kill the parse.

### 3.5 AST node inventory

`ASTNode` (abstract: `SourceLocation loc; Type type = UNRESOLVED; accept(visitor)`) with:

`ProgramNode`, `BlockNode`, `DeclarationNode`, `AssignmentNode`, `IfNode`, `WhileNode`, `PrintNode`, `BinaryExprNode(op)`, `UnaryExprNode(op)`, `IntLiteralNode`, `FloatLiteralNode`, `BoolLiteralNode`, `IdentifierNode`.

Visitor interface: `ASTVisitor { visit(ProgramNode&) … }`. Concrete visitors: `ASTPrinter` (indented text), `SemanticAnalyzer`, `TACGenerator`, and (bonus) `DotPrinter` for Graphviz.

### 3.6 Symbol table design

```cpp
struct Symbol { std::string name; Type type; int scopeLevel; int declaredLine; bool initialized; };
class SymbolTable {
  void enterScope(); void exitScope();
  bool insert(Symbol);                 // false ⇒ redeclaration in current scope
  Symbol* lookup(name);                // innermost→outermost
  Symbol* lookupCurrentScope(name);    // redeclaration check
};
```

Implementation: `std::vector<std::unordered_map<std::string, Symbol>>` as the active stack, plus an archive of exited scopes (scope id, parent id) so `--symtab` can print the *complete* scope tree after analysis. Complexities: insert/lookupCurrent O(1) avg; lookup O(depth).

### 3.7 Semantic rules → error catalogue (traceable to §4.5)

| Rule | Trigger | Message pattern |
|---|---|---|
| S1 Undeclared | `IdentifierNode` not found by `lookup` | `Semantic Error [line L, col C]: Undeclared variable 'x'. Declare it before use, e.g. 'int x;'` |
| S2 Redeclaration | `insert` fails | `…: Redeclaration of variable 'x' (first declared at line N)` |
| S3 Scope violation | Same mechanism as S1 (out-of-scope ⇒ not found), message references prior inner-scope declaration when we can detect it via the archive | `…: Variable 'y' is not visible here; it was declared in an inner block at line N` |
| S4 Type mismatch (assignment) | RHS type ⊄ LHS type per A1 | `…: Cannot assign bool to int` / `…: Possible loss of data assigning float to int` |
| S5 Invalid expression (arith) | bool operand to `+ - * / %`; non-int to `%` | `…: Operator '+' requires numeric operands, got bool` |
| S6 Invalid expression (logical) | non-bool operand to `&& \|\| !` | `…: Operator '&&' requires bool operands, got int` |
| S7 Invalid comparison | mixed bool/numeric to `== !=`; bool to `< …` | per A3/A4 |
| S8 Condition type | `if`/`while` condition not bool | `…: Condition of 'while' must be bool, got int` |

Type inference: bottom-up on expressions; result types per A1–A6; every node annotated (`node.type`) — the "annotated/validated AST" the manual's pipeline diagram names.

### 3.8 TAC design

Instruction set (printed form):

```
x = y op z        binary                t3 = t1 + t2
x = op y          unary                 t1 = -x  |  t1 = !flag
x = y             copy                  a = t2
x = (float) y     widening cast         t1 = (float) n
ifTrue x goto L   / ifFalse x goto L    conditional jump
goto L            unconditional
L:                label
print x           print
```

Control-flow templates: `if` (falseLabel), `if-else` (elseLabel+endLabel), `while` (beginLabel/endLabel with back-jump), `&&`/`||` via short-circuit jump chains; storing a bool expression materializes it (`flag = x>0 && y<3` → jumps assigning `flag = true` / `flag = false`). Temp/label counters reset per compilation; generator is a visitor emitting into `std::vector<TACInstr>`.

### 3.9 Diagnostics format (all phases, uniform)

```
<Category> Error [line L, col C]: <what happened> near '<lexeme>'
  --> hint: <possible fix>
```

Categories: `Lexical`, `Syntax`, `Semantic`. Exit codes: 0 = clean, 1 = errors found (TAC suppressed). This is a superset of the template's expected outputs, so their tests pass under prefix matching.

### 3.10 Build & CLI

- `make` → `bison -d -Wcounterexamples parser.y`, `flex lexer.l`, `g++ -std=c++17 -Wall -Wextra` → `build/mcc`.
- `make test` → `scripts/run_tests.sh` (diffs actual vs `expected/`, prints matrix).
- Usage: `./mcc program.mc [--tokens] [--ast] [--symtab] [--tac] [-o out.tac]` (default: run full pipeline, print diagnostics, emit TAC on success).

---

## 4. Implementation Roadmap

Module order follows the pipeline; each milestone ends in working, tested, committed state. Suggested commit messages included (satisfies §9).

| Phase | Deliverable | Key acceptance criteria | Example commits |
|---|---|---|---|
| **0. Architecture** (this doc) | Finalized design, frozen decisions A1–A11 | Sign-off on type rules & grammar | `Add architecture and design document` |
| **1. Scaffolding** | Repo tree, Makefile skeleton, `.gitignore`, `common/` (SourceLocation, Type, ErrorReporter, token names) | `make` builds an empty driver | `Set up project structure and build system` |
| **2. Lexer** | `lexer.l`, `--tokens` mode | All token classes; line+col tracking; comments (`//`, `/* */`, unterminated-comment error); invalid-token diagnostics; longest match verified (`<=` vs `<`, `123abc` case) | `Add Flex lexer with full token set`, `Add lexical error reporting with line and column` |
| **3. Parser + AST** | `parser.y`, AST classes, `ASTPrinter`, `--ast` mode | 0 conflicts; dangling-else verified; error recovery at `;`/`}`; AST prints for sample program §5.5 | `Implement Bison grammar with precedence declarations`, `Create AST node hierarchy with visitor support`, `Add syntax error recovery` |
| **4. Symbol table** | `SymbolTable` + unit-style tests, `--symtab` dump | Nested scope shadowing correct; archive prints full scope tree | `Implement symbol table with nested scopes` |
| **5. Semantic analyzer** | `SemanticAnalyzer` visitor | All S1–S8 detected; multi-error files report *all* errors; AST annotated with types | `Add semantic analysis for declarations and scopes`, `Implement expression type checking` |
| **6. TAC generator** | `TACGenerator`, `--tac`, `-o` | Manual §4.6 example reproduces `t1 = b * 2 …` exactly; short-circuit verified; all control-flow templates | `Generate TAC for arithmetic expressions`, `Add short-circuit evaluation for logical operators` |
| **7. Test suite** | Full `tests/` + runner | ≥6 valid, ≥1 lexical, ≥2 syntax, ≥1 per semantic rule (≥8), golden outputs, `make test` all green | `Add regression test suite and runner script` |
| **8. README** | Industry-quality README | Overview, pipeline diagram, build/run, examples, structure, phases, screenshots placeholders, limitations, future work | `Write project README` |
| **9. Report** | 14-chapter report per §12 incl. formal CFG | Every chapter present; CFG matches implementation exactly | `Add project report chapters 1-7`, `Complete project report` |
| **10. Presentation** | Slide deck per §13 | Architecture diagram, per-phase walkthrough, live-demo script (valid + each error class + TAC) | `Add presentation slides` |
| **11. Viva pack + final audit** | Per-phase Q&A packs; requirement-traceability checklist at 100% | Every manual requirement mapped to file + test + verified | `Add viva preparation notes`, `Final audit checklist` |

**Deadline safety:** phases 1–6 are the graded core (80% of rubric); target completing them with ≥1 week of buffer before 31 July, leaving docs/slides/viva material for the buffer. Bonus features considered *only* after Phase 7 is green — cheapest high-value picks: **constant folding** (fold literal subtrees in the TAC visitor) and **Graphviz AST** (one extra visitor).

## 5. Requirement Traceability Checklist (to be completed at final audit)

| Manual requirement | Planned artifact | Verified |
|---|---|---|
| §4.1 all lexeme classes + errors | `src/lexer/lexer.l`, `tests/invalid/lexical/*` | ☐ |
| §4.2 CFG, Bison, errors, recovery | `src/parser/parser.y`, `docs/grammar.md`, `tests/invalid/syntax/*` | ☐ |
| §4.3 AST + printing | `src/ast/*`, `--ast` | ☐ |
| §4.4 symbol table, nested scopes, 4 fields | `src/symbol_table/*`, `--symtab` | ☐ |
| §4.5 six semantic error classes | `src/semantic/*`, `tests/invalid/semantic/*` (one per rule) | ☐ |
| §4.6 TAC incl. control flow + print | `src/tac/*`, golden `.tac` files | ☐ |
| §5.5 sample program compiles to TAC | `examples/sample.mc` | ☐ |
| §8 clean structure, §7 stack | repo tree, Makefile | ☐ |
| §9 GitHub practices | commit history, all members | ☐ |
| §11 all deliverables | README, report, slides, tests, screenshots, instructions | ☐ |
| §12 report structure (14 chapters) | `docs/report/` | ☐ |
| §13 presentation content | `docs/slides` + demo script | ☐ |
| §15 test categories | `tests/` matrix | ☐ |

---

*End of Phase 0 document. Code begins only after decisions A1–A11 and the grammar draft are approved.*
