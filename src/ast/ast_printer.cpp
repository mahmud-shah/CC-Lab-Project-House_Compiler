#include "minilang/ast_printer.hpp"

namespace minilang {

void ASTPrinter::print(ASTNode& root) {
    depth_ = 0;
    root.accept(*this);
}

std::ostream& ASTPrinter::line() {
    for (int i = 0; i < depth_; ++i) os_ << "  ";
    return os_;
}

void ASTPrinter::locSuffix(const ASTNode& n) {
    os_ << "  [" << n.loc.line << ":" << n.loc.col << "]\n";
}

void ASTPrinter::typeSuffix(const ExprNode& n) {
    if (n.type != Type::Unresolved) os_ << " : " << toString(n.type);
}

void ASTPrinter::visit(ProgramNode& n) {
    line() << "Program";
    locSuffix(n);
    Indent in(*this);
    for (StmtNode* s : n.statements) s->accept(*this);
}

void ASTPrinter::visit(BlockNode& n) {
    line() << "Block";
    locSuffix(n);
    Indent in(*this);
    for (StmtNode* s : n.statements) s->accept(*this);
}

void ASTPrinter::visit(DeclarationNode& n) {
    line() << "Declaration '" << n.name << "' : " << toString(n.declType);
    locSuffix(n);
}

void ASTPrinter::visit(AssignmentNode& n) {
    line() << "Assignment '" << n.name << "'";
    locSuffix(n);
    Indent in(*this);
    n.value->accept(*this);
}

void ASTPrinter::visit(IfNode& n) {
    line() << (n.elseBranch ? "IfElse" : "If");
    locSuffix(n);
    Indent in(*this);
    line() << "Condition\n";
    {
        Indent in2(*this);
        n.condition->accept(*this);
    }
    line() << "Then\n";
    {
        Indent in2(*this);
        n.thenBranch->accept(*this);
    }
    if (n.elseBranch) {
        line() << "Else\n";
        Indent in2(*this);
        n.elseBranch->accept(*this);
    }
}

void ASTPrinter::visit(WhileNode& n) {
    line() << "While";
    locSuffix(n);
    Indent in(*this);
    line() << "Condition\n";
    {
        Indent in2(*this);
        n.condition->accept(*this);
    }
    line() << "Body\n";
    {
        Indent in2(*this);
        n.body->accept(*this);
    }
}

void ASTPrinter::visit(PrintNode& n) {
    line() << "Print";
    locSuffix(n);
    Indent in(*this);
    n.value->accept(*this);
}

void ASTPrinter::visit(BinaryExprNode& n) {
    line() << "BinaryExpr '" << toString(n.op) << "'";
    typeSuffix(n);
    locSuffix(n);
    Indent in(*this);
    n.lhs->accept(*this);
    n.rhs->accept(*this);
}

void ASTPrinter::visit(UnaryExprNode& n) {
    line() << "UnaryExpr '" << toString(n.op) << "'";
    typeSuffix(n);
    locSuffix(n);
    Indent in(*this);
    n.operand->accept(*this);
}

void ASTPrinter::visit(IntLiteralNode& n) {
    line() << "IntLiteral " << n.value;
    typeSuffix(n);
    locSuffix(n);
}

void ASTPrinter::visit(FloatLiteralNode& n) {
    line() << "FloatLiteral " << n.value;
    typeSuffix(n);
    locSuffix(n);
}

void ASTPrinter::visit(BoolLiteralNode& n) {
    line() << "BoolLiteral " << (n.value ? "true" : "false");
    typeSuffix(n);
    locSuffix(n);
}

void ASTPrinter::visit(IdentifierNode& n) {
    line() << "Identifier '" << n.name << "'";
    typeSuffix(n);
    locSuffix(n);
}

} // namespace minilang
