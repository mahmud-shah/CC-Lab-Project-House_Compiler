/* ============================================================================
 * MiniLang Syntax Analyzer (Bison specification)
 * Project Manual §4.2 + §5
 *
 * Responsibilities:
 *   - implement the complete, unambiguous CFG of MiniLang
 *   - build the AST bottom-up in the rule actions (§4.3)
 *   - report syntax errors with line/column and a fix hint
 *   - recover at statement boundaries (';' and '}') so one error never
 *     hides the rest of the file
 *
 * Ambiguity strategy (documented in docs/grammar/grammar.md):
 *   Expression precedence and associativity are declared with %left/%right
 *   instead of being encoded as eight layered nonterminals. The grammar
 *   stays readable and mirrors §5.3 directly, while Bison's tables resolve
 *   every expression conflict. The dangling else is resolved with a
 *   %precedence pair (ELSE binds tighter than a matched-if reduction),
 *   which is the standard "shift the else" resolution made explicit.
 *   Result: zero shift/reduce and zero reduce/reduce conflicts, verified
 *   at build time with `bison -Wall -Wcounterexamples`.
 * ==========================================================================*/

%code requires {
    #include <vector>

    #include "minilang/ast.hpp"
    #include "minilang/source_location.hpp"

    /* Bison's location type is our own SourceLocation, so every rule can
     * stamp its AST node via @N with no conversion. */
    #define YYLTYPE minilang::SourceLocation
    #define YYLTYPE_IS_DECLARED 1

    /* A rule's location is the location of its first symbol; an empty
     * rule inherits the position just before it. */
    #define YYLLOC_DEFAULT(Cur, Rhs, N)                          \
        do {                                                     \
            (Cur) = (N) ? YYRHSLOC(Rhs, 1) : YYRHSLOC(Rhs, 0);   \
        } while (0)
}

%code {
    #include <cctype>
    #include <cstdlib>
    #include <set>
    #include <string>

    #include "minilang/error_reporter.hpp"

    extern int yylex();

    /* Impure (default) Bison parsers call yyerror with the parse-params
     * and the message only; the offending token's location is read from
     * the global yylloc. */
    void yyerror(minilang::ProgramNode** result, const char* msg);

    using namespace minilang;
}

/* The built AST is handed back through this out-parameter, keeping the
 * parser free of result globals. */
%parse-param { minilang::ProgramNode** result }

%locations
%define parse.error verbose

%union {
    long long                            ival;
    double                               fval;
    int                                  bval;
    char*                                sval;
    minilang::Type                       typeval;
    minilang::ExprNode*                  expr;
    minilang::StmtNode*                  stmt;
    minilang::BlockNode*                 block;
    std::vector<minilang::StmtNode*>*    stmtList;
}

/* ---- terminals (display names improve Bison's error messages) ---------- */
%token TOK_KW_INT     "int"
%token TOK_KW_FLOAT   "float"
%token TOK_KW_BOOL    "bool"
%token TOK_KW_IF      "if"
%token TOK_KW_ELSE    "else"
%token TOK_KW_WHILE   "while"
%token TOK_KW_PRINT   "print"
%token <bval> TOK_KW_TRUE  "true"
%token <bval> TOK_KW_FALSE "false"

%token <sval> TOK_IDENT     "identifier"
%token <ival> TOK_INT_LIT   "integer literal"
%token <fval> TOK_FLOAT_LIT "float literal"

%token TOK_ASSIGN  "="
%token TOK_PLUS    "+"
%token TOK_MINUS   "-"
%token TOK_STAR    "*"
%token TOK_SLASH   "/"
%token TOK_PERCENT "%"
%token TOK_LT      "<"
%token TOK_GT      ">"
%token TOK_LE      "<="
%token TOK_GE      ">="
%token TOK_EQ      "=="
%token TOK_NEQ     "!="
%token TOK_AND     "&&"
%token TOK_OR      "||"
%token TOK_NOT     "!"

%token TOK_LBRACE  "{"
%token TOK_RBRACE  "}"
%token TOK_LPAREN  "("
%token TOK_RPAREN  ")"
%token TOK_SEMI    ";"

/* ---- operator precedence, lowest first (Manual §5.3, decision table in
 * docs/design/ARCHITECTURE_AND_ROADMAP.md §3.4) --------------------------- */
%left TOK_OR
%left TOK_AND
%left TOK_EQ TOK_NEQ
%left TOK_LT TOK_GT TOK_LE TOK_GE
%left TOK_PLUS TOK_MINUS
%left TOK_STAR TOK_SLASH TOK_PERCENT
%precedence TOK_NOT UMINUS

/* ---- dangling else: an if without else reduces with LOWER precedence
 * than the ELSE token shifts, so 'else' always binds to the nearest 'if' */
%precedence LOWER_THAN_ELSE
%precedence TOK_KW_ELSE

/* ---- nonterminal value types ------------------------------------------- */
%type <stmtList> stmt_list
%type <stmt>     stmt declaration assignment if_stmt while_stmt print_stmt
%type <block>    block
%type <expr>     expr
%type <typeval>  type_spec

/* ---- cleanup on error recovery: Bison discards symbols during recovery;
 * these destructors stop those discards from leaking ---------------------- */
%destructor { free($$); }   <sval>
%destructor { delete $$; }  <expr> <stmt> <block>
%destructor {
    for (minilang::StmtNode* s : *$$) delete s;
    delete $$;
} <stmtList>

%initial-action {
    @$ = minilang::SourceLocation{1, 1};
}

%start program

%%

program
    : stmt_list {
          auto* p = new ProgramNode(@$);
          p->statements = std::move(*$1);
          delete $1;
          *result = p;
      }
    ;

stmt_list
    : %empty              { $$ = new std::vector<StmtNode*>(); }
    | stmt_list stmt      {
          if ($2 != nullptr) $1->push_back($2);   /* null = recovered error */
          $$ = $1;
      }
    ;

stmt
    : declaration
    | assignment
    | if_stmt
    | while_stmt
    | print_stmt
    | block               { $$ = $1; }
    | error TOK_SEMI      { $$ = nullptr; yyerrok; }
      /* Recovery point 1: on a syntax error, discard tokens up to the next
       * ';' and continue parsing the following statement. */
    ;

declaration
    : type_spec TOK_IDENT TOK_SEMI {
          $$ = new DeclarationNode($1, $2, @2);
          free($2);
      }
    ;

type_spec
    : TOK_KW_INT    { $$ = Type::Int; }
    | TOK_KW_FLOAT  { $$ = Type::Float; }
    | TOK_KW_BOOL   { $$ = Type::Bool; }
    ;

assignment
    : TOK_IDENT TOK_ASSIGN expr TOK_SEMI {
          $$ = new AssignmentNode($1, $3, @1);
          free($1);
      }
    ;

if_stmt
    : TOK_KW_IF TOK_LPAREN expr TOK_RPAREN stmt %prec LOWER_THAN_ELSE {
          $$ = new IfNode($3, $5, nullptr, @1);
      }
    | TOK_KW_IF TOK_LPAREN expr TOK_RPAREN stmt TOK_KW_ELSE stmt {
          $$ = new IfNode($3, $5, $7, @1);
      }
    ;

while_stmt
    : TOK_KW_WHILE TOK_LPAREN expr TOK_RPAREN stmt {
          $$ = new WhileNode($3, $5, @1);
      }
    ;

print_stmt
    : TOK_KW_PRINT expr TOK_SEMI {
          $$ = new PrintNode($2, @1);
      }
    ;

block
    : TOK_LBRACE stmt_list TOK_RBRACE {
          auto* b = new BlockNode(@1);
          b->statements = std::move(*$2);
          delete $2;
          $$ = b;
      }
    | TOK_LBRACE stmt_list error TOK_RBRACE {
          /* Recovery point 2: an error inside a block that has no ';' left
           * to resynchronize on is closed at the block's '}'. Statements
           * parsed before the error are kept. The rule is anchored after
           * stmt_list so that, in the parser state reached on 'error', this
           * item and recovery point 1 are distinguished by the next token
           * (';' vs '}') - which is what keeps the grammar conflict-free. */
          auto* b = new BlockNode(@1);
          b->statements = std::move(*$2);
          delete $2;
          $$ = b;
          yyerrok;
      }
    ;

expr
    : expr TOK_OR expr        { $$ = new BinaryExprNode(BinaryOp::Or,  $1, $3, @2); }
    | expr TOK_AND expr       { $$ = new BinaryExprNode(BinaryOp::And, $1, $3, @2); }
    | expr TOK_EQ expr        { $$ = new BinaryExprNode(BinaryOp::Eq,  $1, $3, @2); }
    | expr TOK_NEQ expr       { $$ = new BinaryExprNode(BinaryOp::Neq, $1, $3, @2); }
    | expr TOK_LT expr        { $$ = new BinaryExprNode(BinaryOp::Lt,  $1, $3, @2); }
    | expr TOK_GT expr        { $$ = new BinaryExprNode(BinaryOp::Gt,  $1, $3, @2); }
    | expr TOK_LE expr        { $$ = new BinaryExprNode(BinaryOp::Le,  $1, $3, @2); }
    | expr TOK_GE expr        { $$ = new BinaryExprNode(BinaryOp::Ge,  $1, $3, @2); }
    | expr TOK_PLUS expr      { $$ = new BinaryExprNode(BinaryOp::Add, $1, $3, @2); }
    | expr TOK_MINUS expr     { $$ = new BinaryExprNode(BinaryOp::Sub, $1, $3, @2); }
    | expr TOK_STAR expr      { $$ = new BinaryExprNode(BinaryOp::Mul, $1, $3, @2); }
    | expr TOK_SLASH expr     { $$ = new BinaryExprNode(BinaryOp::Div, $1, $3, @2); }
    | expr TOK_PERCENT expr   { $$ = new BinaryExprNode(BinaryOp::Mod, $1, $3, @2); }
    | TOK_NOT expr            { $$ = new UnaryExprNode(UnaryOp::Not, $2, @1); }
    | TOK_MINUS expr %prec UMINUS
                              { $$ = new UnaryExprNode(UnaryOp::Neg, $2, @1); }
    | TOK_LPAREN expr TOK_RPAREN
                              { $$ = $2; }
    | TOK_IDENT               { $$ = new IdentifierNode($1, @1); free($1); }
    | TOK_INT_LIT             { $$ = new IntLiteralNode($1, @1); }
    | TOK_FLOAT_LIT           { $$ = new FloatLiteralNode($1, @1); }
    | TOK_KW_TRUE             { $$ = new BoolLiteralNode(true, @1); }
    | TOK_KW_FALSE            { $$ = new BoolLiteralNode(false, @1); }
    ;

%%

/* Reformats Bison's verbose diagnostic ("syntax error, unexpected X,
 * expecting Y") into the project's uniform format and attaches a fix hint
 * for the most common mistakes. */
void yyerror(minilang::ProgramNode** /*result*/, const char* msg) {
    std::string text = msg;

    const std::string prefix = "syntax error, ";
    if (text.rfind(prefix, 0) == 0) text.erase(0, prefix.size());
    if (!text.empty()) text[0] = static_cast<char>(std::toupper(text[0]));

    /* Bison prints token display names bare ("expecting ;"); wrap every
     * known token spelling in quotes for readability. */
    static const std::set<std::string> tokenSpellings = {
        ";", "(", ")", "{", "}", "=",
        "+", "-", "*", "/", "%",
        "<", ">", "<=", ">=", "==", "!=", "&&", "||", "!",
        "int", "float", "bool", "if", "else", "while", "print",
        "true", "false"
    };
    std::string out;
    std::string word;
    auto flush = [&]() {
        if (word.empty()) return;
        if (tokenSpellings.count(word))
            out += "'" + word + "'";
        else
            out += word;
        word.clear();
    };
    for (char c : text) {
        if (c == ' ' || c == ',') {
            flush();
            out += c;
        } else {
            word += c;
        }
    }
    flush();
    text = std::move(out);

    std::string hint;
    if (text.find("expecting ';'") != std::string::npos)
        hint = "a semicolon may be missing at the end of the previous statement";
    else if (text.find("expecting ')'") != std::string::npos)
        hint = "check for an unclosed '(' earlier on this line";
    else if (text.find("unexpected 'else'") != std::string::npos ||
             text.find("Unexpected 'else'") != std::string::npos)
        hint = "'else' must directly follow the statement of an 'if'";
    else if (text.find("Unexpected '='") != std::string::npos)
        hint = "assignment targets must be a single identifier";
    else if (text.find("Unexpected '{'") != std::string::npos)
        hint = "an expression or ')' may be missing before this '{'";
    else if (text.find("end of file") != std::string::npos)
        hint = "check for an unclosed '{' or a missing ';' on the last statement";

    minilang::ErrorReporter::global().report(
        minilang::ErrorCategory::Syntax, yylloc, std::move(text),
        std::move(hint));
}
