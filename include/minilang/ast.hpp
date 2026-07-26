#ifndef MINILANG_AST_HPP
#define MINILANG_AST_HPP

#include <string>
#include <vector>

#include "minilang/source_location.hpp"
#include "minilang/type.hpp"

namespace minilang {

class ASTVisitor;

// Operators

enum class BinaryOp {
    Add, Sub, Mul, Div, Mod,          // arithmetic  + - * / %
    Lt, Gt, Le, Ge, Eq, Neq,          // relational  < > <= >= == !=
    And, Or                           // logical     && ||
};

enum class UnaryOp {
    Neg,                              // arithmetic negation  -x
    Not                               // logical negation     !b
};

const char* toString(BinaryOp op);
const char* toString(UnaryOp op);

inline bool isArithmetic(BinaryOp op) {
    return op == BinaryOp::Add || op == BinaryOp::Sub ||
           op == BinaryOp::Mul || op == BinaryOp::Div || op == BinaryOp::Mod;
}
inline bool isRelational(BinaryOp op) {
    return op == BinaryOp::Lt || op == BinaryOp::Gt ||
           op == BinaryOp::Le || op == BinaryOp::Ge;
}
inline bool isEquality(BinaryOp op) {
    return op == BinaryOp::Eq || op == BinaryOp::Neq;
}
inline bool isLogical(BinaryOp op) {
    return op == BinaryOp::And || op == BinaryOp::Or;
}

// Base classes

class ASTNode {
public:
    SourceLocation loc;

    virtual ~ASTNode() = default;
    virtual void accept(ASTVisitor& v) = 0;

protected:
    explicit ASTNode(SourceLocation l) : loc(l) {}
};

class ExprNode : public ASTNode {
public:
    Type type = Type::Unresolved;

protected:
    using ASTNode::ASTNode;
};

class StmtNode : public ASTNode {
protected:
    using ASTNode::ASTNode;
};

// Expressions

class IntLiteralNode final : public ExprNode {
public:
    long long value;

    IntLiteralNode(long long v, SourceLocation l) : ExprNode(l), value(v) {}
    void accept(ASTVisitor& v) override;
};

class FloatLiteralNode final : public ExprNode {
public:
    double value;

    FloatLiteralNode(double v, SourceLocation l) : ExprNode(l), value(v) {}
    void accept(ASTVisitor& v) override;
};

class BoolLiteralNode final : public ExprNode {
public:
    bool value;

    BoolLiteralNode(bool v, SourceLocation l) : ExprNode(l), value(v) {}
    void accept(ASTVisitor& v) override;
};

class IdentifierNode final : public ExprNode {
public:
    std::string name;

    IdentifierNode(std::string n, SourceLocation l)
        : ExprNode(l), name(std::move(n)) {}
    void accept(ASTVisitor& v) override;
};

class BinaryExprNode final : public ExprNode {
public:
    BinaryOp  op;
    ExprNode* lhs;
    ExprNode* rhs;

    BinaryExprNode(BinaryOp o, ExprNode* l, ExprNode* r, SourceLocation loc)
        : ExprNode(loc), op(o), lhs(l), rhs(r) {}
    ~BinaryExprNode() override { delete lhs; delete rhs; }
    void accept(ASTVisitor& v) override;
};

class UnaryExprNode final : public ExprNode {
public:
    UnaryOp   op;
    ExprNode* operand;

    UnaryExprNode(UnaryOp o, ExprNode* e, SourceLocation loc)
        : ExprNode(loc), op(o), operand(e) {}
    ~UnaryExprNode() override { delete operand; }
    void accept(ASTVisitor& v) override;
};

// Statements

class DeclarationNode final : public StmtNode {
public:
    Type        declType;   // int, float, or bool
    std::string name;

    DeclarationNode(Type t, std::string n, SourceLocation l)
        : StmtNode(l), declType(t), name(std::move(n)) {}
    void accept(ASTVisitor& v) override;
};

class AssignmentNode final : public StmtNode {
public:
    std::string name;
    ExprNode*   value;
    Type        targetType = Type::Unresolved;

    AssignmentNode(std::string n, ExprNode* v, SourceLocation l)
        : StmtNode(l), name(std::move(n)), value(v) {}
    ~AssignmentNode() override { delete value; }
    void accept(ASTVisitor& v) override;
};

class BlockNode final : public StmtNode {
public:
    std::vector<StmtNode*> statements;

    explicit BlockNode(SourceLocation l) : StmtNode(l) {}
    ~BlockNode() override {
        for (StmtNode* s : statements) delete s;
    }
    void accept(ASTVisitor& v) override;
};

class IfNode final : public StmtNode {
public:
    ExprNode* condition;
    StmtNode* thenBranch;
    StmtNode* elseBranch;   // nullptr when the if has no else

    IfNode(ExprNode* c, StmtNode* t, StmtNode* e, SourceLocation l)
        : StmtNode(l), condition(c), thenBranch(t), elseBranch(e) {}
    ~IfNode() override {
        delete condition;
        delete thenBranch;
        delete elseBranch;
    }
    void accept(ASTVisitor& v) override;
};

class WhileNode final : public StmtNode {
public:
    ExprNode* condition;
    StmtNode* body;

    WhileNode(ExprNode* c, StmtNode* b, SourceLocation l)
        : StmtNode(l), condition(c), body(b) {}
    ~WhileNode() override {
        delete condition;
        delete body;
    }
    void accept(ASTVisitor& v) override;
};

class PrintNode final : public StmtNode {
public:
    ExprNode* value;

    PrintNode(ExprNode* v, SourceLocation l) : StmtNode(l), value(v) {}
    ~PrintNode() override { delete value; }
    void accept(ASTVisitor& v) override;
};

// Root

class ProgramNode final : public ASTNode {
public:
    std::vector<StmtNode*> statements;

    explicit ProgramNode(SourceLocation l) : ASTNode(l) {}
    ~ProgramNode() override {
        for (StmtNode* s : statements) delete s;
    }
    void accept(ASTVisitor& v) override;
};

// Visitor interface - one method per concrete node

class ASTVisitor {
public:
    virtual ~ASTVisitor() = default;

    virtual void visit(ProgramNode& n)      = 0;
    virtual void visit(BlockNode& n)        = 0;
    virtual void visit(DeclarationNode& n)  = 0;
    virtual void visit(AssignmentNode& n)   = 0;
    virtual void visit(IfNode& n)           = 0;
    virtual void visit(WhileNode& n)        = 0;
    virtual void visit(PrintNode& n)        = 0;
    virtual void visit(BinaryExprNode& n)   = 0;
    virtual void visit(UnaryExprNode& n)    = 0;
    virtual void visit(IntLiteralNode& n)   = 0;
    virtual void visit(FloatLiteralNode& n) = 0;
    virtual void visit(BoolLiteralNode& n)  = 0;
    virtual void visit(IdentifierNode& n)   = 0;
};

} 

#endif 
