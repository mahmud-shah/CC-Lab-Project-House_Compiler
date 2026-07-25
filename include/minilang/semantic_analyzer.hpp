#ifndef MINILANG_SEMANTIC_ANALYZER_HPP
#define MINILANG_SEMANTIC_ANALYZER_HPP

#include "minilang/ast.hpp"
#include "minilang/error_reporter.hpp"
#include "minilang/symbol_table.hpp"
#include "minilang/type.hpp"

namespace minilang {

class SemanticAnalyzer final : public ASTVisitor {
public:
    explicit SemanticAnalyzer(ErrorReporter& reporter);


    bool analyze(ProgramNode& root);

    const SymbolTable& symbolTable() const { return table_; }
    SymbolTable&       symbolTable()       { return table_; }

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
    ErrorReporter& reporter_;
    SymbolTable    table_;

    void semanticError(SourceLocation loc,
                       std::string    message,
                       std::string    hint = "");


    Type resolveArithmetic(BinaryExprNode& n, Type lhs, Type rhs);
    Type resolveRelational(BinaryExprNode& n, Type lhs, Type rhs);
    Type resolveEquality  (BinaryExprNode& n, Type lhs, Type rhs);
    Type resolveLogical   (BinaryExprNode& n, Type lhs, Type rhs);
};

} 

#endif 
