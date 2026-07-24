#include "minilang/ast.hpp"

// accept() is the second half of visitor double-dispatch: each node calls
// the visit overload for its own concrete type, so a visitor never needs
// to inspect node kinds or downcast.

namespace minilang {

const char* toString(BinaryOp op) {
    switch (op) {
        case BinaryOp::Add: return "+";
        case BinaryOp::Sub: return "-";
        case BinaryOp::Mul: return "*";
        case BinaryOp::Div: return "/";
        case BinaryOp::Mod: return "%";
        case BinaryOp::Lt:  return "<";
        case BinaryOp::Gt:  return ">";
        case BinaryOp::Le:  return "<=";
        case BinaryOp::Ge:  return ">=";
        case BinaryOp::Eq:  return "==";
        case BinaryOp::Neq: return "!=";
        case BinaryOp::And: return "&&";
        case BinaryOp::Or:  return "||";
    }
    return "?";
}

const char* toString(UnaryOp op) {
    switch (op) {
        case UnaryOp::Neg: return "-";
        case UnaryOp::Not: return "!";
    }
    return "?";
}

void ProgramNode::accept(ASTVisitor& v)      { v.visit(*this); }
void BlockNode::accept(ASTVisitor& v)        { v.visit(*this); }
void DeclarationNode::accept(ASTVisitor& v)  { v.visit(*this); }
void AssignmentNode::accept(ASTVisitor& v)   { v.visit(*this); }
void IfNode::accept(ASTVisitor& v)           { v.visit(*this); }
void WhileNode::accept(ASTVisitor& v)        { v.visit(*this); }
void PrintNode::accept(ASTVisitor& v)        { v.visit(*this); }
void BinaryExprNode::accept(ASTVisitor& v)   { v.visit(*this); }
void UnaryExprNode::accept(ASTVisitor& v)    { v.visit(*this); }
void IntLiteralNode::accept(ASTVisitor& v)   { v.visit(*this); }
void FloatLiteralNode::accept(ASTVisitor& v) { v.visit(*this); }
void BoolLiteralNode::accept(ASTVisitor& v)  { v.visit(*this); }
void IdentifierNode::accept(ASTVisitor& v)   { v.visit(*this); }

} // namespace minilang
