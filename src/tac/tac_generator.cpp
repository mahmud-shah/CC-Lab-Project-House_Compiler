#include "minilang/tac_generator.hpp"

#include <sstream>

namespace minilang {

TACGenerator::TACGenerator(TACProgram& prog) : prog_(prog) {}

void TACGenerator::generate(ProgramNode& root) {
    root.accept(*this);
}

std::string TACGenerator::newTemp() {
    return "t" + std::to_string(++tempCount_);
}

std::string TACGenerator::newLabel() {
    return "L" + std::to_string(++labelCount_);
}

void TACGenerator::emit(TACInstr instr) {
    prog_.emit(std::move(instr));
}


void TACGenerator::visit(IntLiteralNode& n) {
    currentResult_ = std::to_string(n.value);
}

void TACGenerator::visit(FloatLiteralNode& n) {
    std::ostringstream oss;
    oss << n.value;
    currentResult_ = oss.str();
}

void TACGenerator::visit(BoolLiteralNode& n) {
    currentResult_ = n.value ? "true" : "false";
}

// Identifier node

void TACGenerator::visit(IdentifierNode& n) {
    currentResult_ = n.name;
}

// Binary expression

void TACGenerator::visit(BinaryExprNode& n) {

    if (n.op == BinaryOp::And) { visitAndExpr(n); return; }
    if (n.op == BinaryOp::Or)  { visitOrExpr(n);  return; }

    n.lhs->accept(*this);
    std::string lhs = currentResult_;

    n.rhs->accept(*this);
    std::string rhs = currentResult_;

    std::string result = newTemp();

    TACInstr::Op op;
    switch (n.op) {
        case BinaryOp::Add: op = TACInstr::Op::Add; break;
        case BinaryOp::Sub: op = TACInstr::Op::Sub; break;
        case BinaryOp::Mul: op = TACInstr::Op::Mul; break;
        case BinaryOp::Div: op = TACInstr::Op::Div; break;
        case BinaryOp::Mod: op = TACInstr::Op::Mod; break;
        case BinaryOp::Lt:  op = TACInstr::Op::Lt;  break;
        case BinaryOp::Gt:  op = TACInstr::Op::Gt;  break;
        case BinaryOp::Le:  op = TACInstr::Op::Le;  break;
        case BinaryOp::Ge:  op = TACInstr::Op::Ge;  break;
        case BinaryOp::Eq:  op = TACInstr::Op::Eq;  break;
        case BinaryOp::Neq: op = TACInstr::Op::Neq; break;
        default: return;
    }

    emit({op, result, lhs, rhs});
    currentResult_ = result;
}

// ---- Short-circuit AND
//
//
//     [evaluate lhs → lhsTemp]
//     ifFalse lhsTemp goto L_false
//     [evaluate rhs → rhsTemp]
//     ifFalse rhsTemp goto L_false
//     result = true
//     goto L_end
// L_false:
//     result = false
// L_end:
//
void TACGenerator::visitAndExpr(BinaryExprNode& n) {
    std::string result = newTemp();
    std::string lFalse = newLabel();
    std::string lEnd   = newLabel();

    n.lhs->accept(*this);
    emit({TACInstr::Op::IfFalse, "", currentResult_, lFalse});

    n.rhs->accept(*this);
    emit({TACInstr::Op::IfFalse, "", currentResult_, lFalse});

    emit({TACInstr::Op::AssignBool, result, "true",  ""});
    emit({TACInstr::Op::Goto,       "",     lEnd,    ""});

    emit({TACInstr::Op::Label,      lFalse, "",      ""});
    emit({TACInstr::Op::AssignBool, result, "false", ""});

    emit({TACInstr::Op::Label,      lEnd,   "",      ""});

    currentResult_ = result;
}

// ---- Short-circuit OR  
//
//
//     [evaluate lhs → lhsTemp]
//     ifTrue lhsTemp goto L_true
//     [evaluate rhs → rhsTemp]
//     ifTrue rhsTemp goto L_true
//     result = false
//     goto L_end
// L_true:
//     result = true
// L_end:
//
void TACGenerator::visitOrExpr(BinaryExprNode& n) {
    std::string result = newTemp();
    std::string lTrue  = newLabel();
    std::string lEnd   = newLabel();

    n.lhs->accept(*this);
    emit({TACInstr::Op::IfTrue,  "", currentResult_, lTrue});

    n.rhs->accept(*this);
    emit({TACInstr::Op::IfTrue,  "", currentResult_, lTrue});

    emit({TACInstr::Op::AssignBool, result, "false", ""});
    emit({TACInstr::Op::Goto,       "",     lEnd,    ""});

    emit({TACInstr::Op::Label,      lTrue,  "",      ""});
    emit({TACInstr::Op::AssignBool, result, "true",  ""});

    emit({TACInstr::Op::Label,      lEnd,   "",      ""});

    currentResult_ = result;
}

// Unary expression

void TACGenerator::visit(UnaryExprNode& n) {
    n.operand->accept(*this);

    std::string result = newTemp();
    TACInstr::Op op    = (n.op == UnaryOp::Neg)
                         ? TACInstr::Op::Neg
                         : TACInstr::Op::Not;

    emit({op, result, currentResult_, ""});
    currentResult_ = result;
}

// Statements

void TACGenerator::visit(ProgramNode& n) {
    for (StmtNode* s : n.statements) s->accept(*this);
}

void TACGenerator::visit(BlockNode& n) {
    for (StmtNode* s : n.statements) s->accept(*this);
}

void TACGenerator::visit(DeclarationNode& /*n*/) {}

// ---- Assignment 

void TACGenerator::visit(AssignmentNode& n) {
    n.value->accept(*this);
    std::string rhs = currentResult_;

    if (n.targetType == Type::Float && n.value->type == Type::Int) {
        std::string castTemp = newTemp();
        emit({TACInstr::Op::CastFloat, castTemp, rhs, ""});
        rhs = castTemp;
    }

    emit({TACInstr::Op::Copy, n.name, rhs, ""});
}

// ---- If / If-else 
//
// if (cond) stmt
//     [evaluate cond → t]
//     ifFalse t goto L_end
//     [then-stmt TAC]
// L_end:
//
// if (cond) stmt else stmt
//     [evaluate cond → t]
//     ifFalse t goto L_else
//     [then-stmt TAC]
//     goto L_end
// L_else:
//     [else-stmt TAC]
// L_end:
//

void TACGenerator::visit(IfNode& n) {
    n.condition->accept(*this);
    std::string cond = currentResult_;

    if (n.elseBranch) {
        std::string lElse = newLabel();
        std::string lEnd  = newLabel();

        emit({TACInstr::Op::IfFalse, "",     cond,  lElse});
        n.thenBranch->accept(*this);
        emit({TACInstr::Op::Goto,    "",     lEnd,  ""});
        emit({TACInstr::Op::Label,   lElse,  "",    ""});
        n.elseBranch->accept(*this);
        emit({TACInstr::Op::Label,   lEnd,   "",    ""});
    } else {
        std::string lEnd = newLabel();

        emit({TACInstr::Op::IfFalse, "",     cond,  lEnd});
        n.thenBranch->accept(*this);
        emit({TACInstr::Op::Label,   lEnd,   "",    ""});
    }
}

// ---- While 
//
// while (cond) stmt
// L_begin:
//     [evaluate cond → t]
//     ifFalse t goto L_end
//     [body TAC]
//     goto L_begin
// L_end:
//

void TACGenerator::visit(WhileNode& n) {
    std::string lBegin = newLabel();
    std::string lEnd   = newLabel();

    emit({TACInstr::Op::Label,   lBegin, "",     ""});
    n.condition->accept(*this);
    std::string cond = currentResult_;
    emit({TACInstr::Op::IfFalse, "",     cond,   lEnd});
    n.body->accept(*this);
    emit({TACInstr::Op::Goto,    "",     lBegin, ""});
    emit({TACInstr::Op::Label,   lEnd,   "",     ""});
}

// ---- Print 

void TACGenerator::visit(PrintNode& n) {
    n.value->accept(*this);
    emit({TACInstr::Op::Print, "", currentResult_, ""});
}

}
