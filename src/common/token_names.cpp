#include "minilang/lexer.hpp"
#include "parser.tab.hpp"

namespace minilang {

const char* tokenName(int kind) {
    switch (kind) {
        case 0:             return "EOF";

        case TOK_KW_INT:    return "KEYWORD_INT";
        case TOK_KW_FLOAT:  return "KEYWORD_FLOAT";
        case TOK_KW_BOOL:   return "KEYWORD_BOOL";
        case TOK_KW_IF:     return "KEYWORD_IF";
        case TOK_KW_ELSE:   return "KEYWORD_ELSE";
        case TOK_KW_WHILE:  return "KEYWORD_WHILE";
        case TOK_KW_PRINT:  return "KEYWORD_PRINT";
        case TOK_KW_TRUE:   return "BOOL_LITERAL";
        case TOK_KW_FALSE:  return "BOOL_LITERAL";

        case TOK_IDENT:     return "IDENTIFIER";
        case TOK_INT_LIT:   return "INT_LITERAL";
        case TOK_FLOAT_LIT: return "FLOAT_LITERAL";

        case TOK_ASSIGN:    return "ASSIGN";
        case TOK_PLUS:      return "PLUS";
        case TOK_MINUS:     return "MINUS";
        case TOK_STAR:      return "STAR";
        case TOK_SLASH:     return "SLASH";
        case TOK_PERCENT:   return "PERCENT";
        case TOK_LT:        return "LESS";
        case TOK_GT:        return "GREATER";
        case TOK_LE:        return "LESS_EQUAL";
        case TOK_GE:        return "GREATER_EQUAL";
        case TOK_EQ:        return "EQUAL";
        case TOK_NEQ:       return "NOT_EQUAL";
        case TOK_AND:       return "AND";
        case TOK_OR:        return "OR";
        case TOK_NOT:       return "NOT";

        case TOK_LBRACE:    return "LBRACE";
        case TOK_RBRACE:    return "RBRACE";
        case TOK_LPAREN:    return "LPAREN";
        case TOK_RPAREN:    return "RPAREN";
        case TOK_SEMI:      return "SEMICOLON";
    }
    return "UNKNOWN";
}

} // namespace minilang
