# MiniLang — Formal Grammar Specification

This document is the authoritative CFG implemented by `src/parser/parser.y`
and is reproduced in the project report (Chapter: Language Specification /
Parser Design). It matches Project Manual §5 exactly; no construct has been
added or removed.

## 1. Notation

Nonterminals are lowercase; terminals are quoted or written in CAPS.
`ε` denotes the empty string. The start symbol is `program`.

## 2. Context-Free Grammar

```
program     → stmt_list

stmt_list   → stmt_list stmt
            | ε

stmt        → declaration
            | assignment
            | if_stmt
            | while_stmt
            | print_stmt
            | block

declaration → type IDENT ';'

type        → 'int' | 'float' | 'bool'

assignment  → IDENT '=' expr ';'

if_stmt     → 'if' '(' expr ')' stmt
            | 'if' '(' expr ')' stmt 'else' stmt

while_stmt  → 'while' '(' expr ')' stmt

print_stmt  → 'print' expr ';'

block       → '{' stmt_list '}'

expr        → expr '||' expr
            | expr '&&' expr
            | expr '==' expr | expr '!=' expr
            | expr '<'  expr | expr '>'  expr
            | expr '<=' expr | expr '>=' expr
            | expr '+'  expr | expr '-'  expr
            | expr '*'  expr | expr '/'  expr | expr '%' expr
            | '!' expr
            | '-' expr                    (unary minus)
            | '(' expr ')'
            | IDENT
            | INT_LIT | FLOAT_LIT | 'true' | 'false'
```

Lexical terminals (defined by the lexer, Manual §5.4):
`IDENT = [A-Za-z_][A-Za-z0-9_]*`, `INT_LIT = [0-9]+`,
`FLOAT_LIT = [0-9]+ '.' [0-9]+`.

## 3. Ambiguity and Its Resolution

The `expr` productions above are deliberately written in the ambiguous
"natural" form and disambiguated by Bison precedence declarations rather
than by rewriting the grammar into eight layered nonterminals
(`logical_or → logical_and → equality → …`). Both approaches are standard;
the declaration approach was chosen because the grammar then mirrors the
manual's operator table §5.3 line-for-line, the parse tables are identical,
and the AST-building actions stay flat and readable.

Precedence levels, lowest binding first (all binary operators are
left-associative; unary operators are non-associative prefix):

| Level | Operators            | Associativity |
|------:|----------------------|---------------|
| 1     | `\|\|`               | left |
| 2     | `&&`                 | left |
| 3     | `==` `!=`            | left |
| 4     | `<` `>` `<=` `>=`    | left |
| 5     | `+` `-` (binary)     | left |
| 6     | `*` `/` `%`          | left |
| 7     | `!`, `-` (unary)     | prefix (`%precedence`, `%prec UMINUS`) |

Consequences verified by AST-shape tests:
`1 + 2 * 3 - 10 % 4 / 2` parses as `(1 + (2*3)) − ((10%4)/2)`, and
`a - b - c` parses as `(a - b) - c`.

### Dangling else

`if (c1) if (c2) s1 else s2` is ambiguous in the raw grammar. MiniLang
adopts the conventional resolution: **`else` binds to the nearest
unmatched `if`**. In the implementation, the else-less production carries
`%prec LOWER_THAN_ELSE` while the `else` token is declared with higher
precedence, so the parser always shifts `else` instead of reducing the
inner `if` — the standard "prefer shift" resolution made explicit rather
than left as a default-resolved conflict.

## 4. Conflict Freedom

The build invokes Bison as:

```
bison -Wall -Wcounterexamples -Werror=conflicts-sr -Werror=conflicts-rr ...
```

so any shift/reduce or reduce/reduce conflict fails the build and prints a
full counterexample derivation. The shipped grammar compiles with **zero
conflicts**.

(Development note kept for the report's Challenges chapter: an early
version had one shift/reduce conflict between the two error-recovery
productions; `-Wcounterexamples` printed the two derivations, and the fix
was to anchor block recovery after `stmt_list` — see §5.)

## 5. Error Detection and Recovery

Two dedicated recovery productions resynchronize the parser so that one
syntax error never hides the rest of the file:

```
stmt   → error ';'                 (discard to the next semicolon)
block  → '{' stmt_list error '}'   (close a broken block at its brace)
```

The second rule is anchored *after* `stmt_list`: when an `error` token is
shifted inside a block, both recovery items occupy the same parser state
and the next terminal (`;` vs `}`) selects between them — this is what
keeps the grammar conflict-free while providing two sync points.
Recovered statements are represented as null and skipped during AST
construction; statements parsed before an in-block error are preserved.

Syntax diagnostics use Bison's verbose error reporting, reformatted into
the project's uniform style with the offending token's line and column
(from `%locations`, whose location type is the project-wide
`SourceLocation`) plus a fix hint for common mistakes, e.g.:

```
Syntax Error [line 2, col 1]: Unexpected identifier, expecting ';'
  --> hint: a semicolon may be missing at the end of the previous statement
```

## 6. AST Mapping

Each production's action constructs exactly one AST node (Manual §4.3):
`program → ProgramNode`, `block → BlockNode`, `declaration →
DeclarationNode`, `assignment → AssignmentNode`, `if_stmt → IfNode`
(else branch nullable), `while_stmt → WhileNode`, `print_stmt →
PrintNode`, binary/unary `expr` alternatives → `BinaryExprNode` /
`UnaryExprNode`, and leaves → literal / identifier nodes. Parentheses and
semicolons produce no nodes — they exist only to shape the tree, which is
the definition of an *abstract* (rather than concrete) syntax tree.
