/* ============================================================================
 * MiniLang Lexical Analyzer (Flex specification)
 * Project Manual §4.1
 *
 * Responsibilities:
 *   - group raw characters into the token classes of §5 (keywords,
 *     identifiers, int/float/bool literals, operators, delimiters)
 *   - discard comments (// line and block) and whitespace
 *   - track line AND column of every token for diagnostics
 *   - report every invalid character sequence as a Lexical Error with a
 *     location and a fix hint, then keep scanning (error recovery)
 *
 * Keyword-vs-identifier strategy: keyword rules are listed before the
 * identifier rule. Flex resolves equal-length matches by rule order, and
 * the longest-match rule guarantees that e.g. "integer" matches the
 * identifier rule (8 chars) rather than keyword "int" (3 chars).
 * ==========================================================================*/

%option noyywrap nounput noinput
%option never-interactive

%{
#include <cstdlib>
#include <cstring>
#include <string>

#include "minilang/error_reporter.hpp"
#include "minilang/lexer.hpp"
#include "parser.tab.hpp"   /* token codes, yylval, yylloc - Bison-generated */

namespace minilang {
SourceLocation ml_token_loc;
} // namespace minilang

using minilang::ErrorCategory;
using minilang::ErrorReporter;

namespace {
int cur_line = 1;
int cur_col  = 1;

/* Location where the current block comment opened - reported if the
 * comment is never closed before end of file. */
minilang::SourceLocation comment_start_loc;

void lexError(const std::string& message, const std::string& hint = "") {
    ErrorReporter::global().report(ErrorCategory::Lexical,
                                   minilang::ml_token_loc, message, hint);
}
} // namespace

/* Runs before every rule action: record the token's start position, then
 * advance the column by the lexeme length. Newlines reset the counters in
 * their own rule actions after this macro has run. */
#define YY_USER_ACTION                                    \
    minilang::ml_token_loc = {cur_line, cur_col};         \
    yylloc = minilang::ml_token_loc;                      \
    cur_col += yyleng;
%}

/* Exclusive start condition for block comments (slash-star ... star-slash) */
%x BLOCK_COMMENT

DIGIT       [0-9]
LETTER      [A-Za-z_]
IDENT       {LETTER}({LETTER}|{DIGIT})*
INT_LIT     {DIGIT}+
FLOAT_LIT   {DIGIT}+"."{DIGIT}+

%%

 /* ---------------- comments (discarded, never tokenized) -------------- */

"//"[^\n]*              { /* line comment: discard to end of line */ }

"/*"                    { comment_start_loc = minilang::ml_token_loc;
                          BEGIN(BLOCK_COMMENT); }
<BLOCK_COMMENT>{
    "*/"                { BEGIN(INITIAL); }
    [^*\n]+             { /* comment body */ }
    "*"                 { /* lone star inside comment */ }
    \n                  { ++cur_line; cur_col = 1; }
    <<EOF>>             { minilang::ml_token_loc = comment_start_loc;
                          lexError("Unterminated block comment",
                                   "close the comment with '*/'");
                          BEGIN(INITIAL);
                          return 0; /* end of input */ }
}

 /* ---------------- whitespace (discarded) ----------------------------- */

[ \t\r]+                { /* discard */ }
\n                      { ++cur_line; cur_col = 1; }

 /* ---------------- keywords (before the identifier rule) -------------- */

"int"                   { return TOK_KW_INT; }
"float"                 { return TOK_KW_FLOAT; }
"bool"                  { return TOK_KW_BOOL; }
"if"                    { return TOK_KW_IF; }
"else"                  { return TOK_KW_ELSE; }
"while"                 { return TOK_KW_WHILE; }
"print"                 { return TOK_KW_PRINT; }
"true"                  { yylval.bval = 1; return TOK_KW_TRUE; }
"false"                 { yylval.bval = 0; return TOK_KW_FALSE; }

 /* ---------------- literals and identifiers --------------------------- */

 /* Malformed numeric forms are trapped BEFORE the valid rules below can
  * split them into misleading token pairs. Longest match makes these
  * rules win over INT_LIT/FLOAT_LIT for the same input. */

{DIGIT}+"."{DIGIT}+"."[0-9.]* {
                          lexError(std::string("Malformed number '") + yytext +
                                       "' has more than one decimal point",
                                   "write a float as digits.digits, e.g. 3.14");
                        }

{DIGIT}+"."/[^0-9]      { lexError(std::string("Malformed float literal '") +
                                       yytext + "' has no digits after the "
                                       "decimal point",
                                   "write e.g. '" + std::string(yytext) + "0'");
                        }

({FLOAT_LIT}|{INT_LIT}){LETTER}({LETTER}|{DIGIT})* {
                          lexError(std::string("Invalid token '") + yytext +
                                       "': identifiers may not start with a digit",
                                   "identifiers must start with a letter or '_'");
                        }

{FLOAT_LIT}             { yylval.fval = std::atof(yytext);
                          return TOK_FLOAT_LIT; }

{INT_LIT}               { yylval.ival = std::atoll(yytext);
                          return TOK_INT_LIT; }

{IDENT}                 { yylval.sval = strdup(yytext);
                          return TOK_IDENT; }

 /* ---------------- operators (multi-char before single-char) ---------- */

"<="                    { return TOK_LE; }
">="                    { return TOK_GE; }
"=="                    { return TOK_EQ; }
"!="                    { return TOK_NEQ; }
"&&"                    { return TOK_AND; }
"||"                    { return TOK_OR; }

"<"                     { return TOK_LT; }
">"                     { return TOK_GT; }
"!"                     { return TOK_NOT; }
"="                     { return TOK_ASSIGN; }
"+"                     { return TOK_PLUS; }
"-"                     { return TOK_MINUS; }
"*"                     { return TOK_STAR; }
"/"                     { return TOK_SLASH; }
"%"                     { return TOK_PERCENT; }

 /* Near-miss operators get targeted hints instead of a generic error. */
"&"                     { lexError("Invalid token '&'",
                                   "logical AND in MiniLang is '&&'"); }
"|"                     { lexError("Invalid token '|'",
                                   "logical OR in MiniLang is '||'"); }

 /* ---------------- delimiters ----------------------------------------- */

"{"                     { return TOK_LBRACE; }
"}"                     { return TOK_RBRACE; }
"("                     { return TOK_LPAREN; }
")"                     { return TOK_RPAREN; }
";"                     { return TOK_SEMI; }

 /* ---------------- catch-all: any other character is a lexical error -- */

.                       { lexError(std::string("Invalid token '") + yytext + "'",
                                   "this character is not part of the "
                                   "MiniLang alphabet"); }

%%

namespace minilang {

void lexerInit(std::FILE* input) {
    yyin     = input;
    cur_line = 1;
    cur_col  = 1;
    yyrestart(input);
    BEGIN(INITIAL);
}

} // namespace minilang
