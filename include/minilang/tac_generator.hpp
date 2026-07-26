#ifndef MINILANG_TAC_GENERATOR_HPP
#define MINILANG_TAC_GENERATOR_HPP

#include <string>

#include "minilang/ast.hpp"
#include "minilang/tac.hpp"


namespace minilang {

class TACGenerator final : public ASTVisitor {
public:
    explicit TACGenerator(TACProgram& prog);

    void generate(ProgramNode& root);

    // ---- ASTVisitor interface 
    void visit(ProgramNode& n)      override;
    void visit(BlockNode& n)        override;
    void visit(DeclarationNode& n)  override;
    void visit(AssignmentNode& n)   override;
    void visit(IfNode& n)           override;
    void visit(WhileNode& n)        override;
    void visit(PrintNode& n)        override;
    void visit(BinaryExprNode& n)   override;
    void visit(UnaryExprNode& n)    override;
    void visit(IntLiteralNode& n)   override;
    void visit(FloatLiteralNode& n) override;
    void visit(BoolLiteralNode& n)  override;
    void visit(IdentifierNode& n)   override;

private:
    TACProgram& prog_;
    int         tempCount_  = 0;
    int         labelCount_ = 0;

    std::string currentResult_;

    std::string newTemp(); 
    std::string newLabel();
    void        emit(TACInstr instr);

    void visitAndExpr(BinaryExprNode& n);
    void visitOrExpr (BinaryExprNode& n);
};

} 

#endif 
