#ifndef MINILANG_AST_PRINTER_HPP
#define MINILANG_AST_PRINTER_HPP

#include <ostream>

#include "minilang/ast.hpp"

namespace minilang {

// Prints the AST as an indented text tree (Project Manual §4.3: "text-based
// indentation is sufficient"). Each line shows the node kind, its payload,
// its source location, and - once semantic analysis has run - the inferred
// type of every expression, which makes this printer double as a debugging
// view of the annotated AST.
class ASTPrinter final : public ASTVisitor {
public:
    explicit ASTPrinter(std::ostream& os) : os_(os) {}

    void print(ASTNode& root);

    void visit(ProgramNode& n) override;
    void visit(BlockNode& n) override;
    void visit(DeclarationNode& n) override;
    void visit(AssignmentNode& n) override;
    void visit(IfNode& n) override;
    void visit(WhileNode& n) override;
    void visit(PrintNode& n) override;
    void visit(BinaryExprNode& n) override;
    void visit(UnaryExprNode& n) override;
    void visit(IntLiteralNode& n) override;
    void visit(FloatLiteralNode& n) override;
    void visit(BoolLiteralNode& n) override;
    void visit(IdentifierNode& n) override;

private:
    std::ostream& os_;
    int           depth_ = 0;

    // RAII helper: indents one level for the lifetime of a child visit.
    struct Indent {
        explicit Indent(ASTPrinter& p) : p_(p) { ++p_.depth_; }
        ~Indent() { --p_.depth_; }
        ASTPrinter& p_;
    };

    std::ostream& line();                       // writes indentation
    void          locSuffix(const ASTNode& n);  // writes " [line:col]\n"
    void          typeSuffix(const ExprNode& n);// writes " : type" if resolved
};

} // namespace minilang

#endif // MINILANG_AST_PRINTER_HPP
