#include "minilang/semantic_analyzer.hpp"

#include <string>

namespace minilang {

// Constructor and public interface

SemanticAnalyzer::SemanticAnalyzer(ErrorReporter& reporter)
    : reporter_(reporter) {}

bool SemanticAnalyzer::analyze(ProgramNode& root) {
    std::size_t errorsBefore = reporter_.errorCount();
    root.accept(*this);
    return reporter_.errorCount() == errorsBefore;
}

void SemanticAnalyzer::semanticError(SourceLocation loc,
                                     std::string    message,
                                     std::string    hint) {
    reporter_.report(ErrorCategory::Semantic, loc,
                     std::move(message), std::move(hint));
}

void SemanticAnalyzer::visit(IntLiteralNode& n) {
    n.type = Type::Int;
}

void SemanticAnalyzer::visit(FloatLiteralNode& n) {
    n.type = Type::Float;
}

void SemanticAnalyzer::visit(BoolLiteralNode& n) {
    n.type = Type::Bool;
}


void SemanticAnalyzer::visit(IdentifierNode& n) {
    Symbol* sym = table_.lookup(n.name);
    if (!sym) {
        
        semanticError(n.loc,
            "Undeclared variable '" + n.name + "'",
            "declare it before use, e.g. 'int " + n.name + ";'");
        n.type = Type::Error;
        return;
    }
    n.type = sym->type;
}


void SemanticAnalyzer::visit(BinaryExprNode& n) {

    n.lhs->accept(*this);
    n.rhs->accept(*this);

    Type lhs = n.lhs->type;
    Type rhs = n.rhs->type;

    if (lhs == Type::Error || rhs == Type::Error) {
        n.type = Type::Error;
        return;
    }

    if      (isArithmetic(n.op)) n.type = resolveArithmetic(n, lhs, rhs);
    else if (isRelational (n.op)) n.type = resolveRelational(n, lhs, rhs);
    else if (isEquality   (n.op)) n.type = resolveEquality  (n, lhs, rhs);
    else if (isLogical    (n.op)) n.type = resolveLogical   (n, lhs, rhs);
    else                          n.type = Type::Error;
}

// ---- Arithmetic: +  -  *  /  % 

Type SemanticAnalyzer::resolveArithmetic(BinaryExprNode& n,
                                         Type lhs, Type rhs) {

    if (n.op == BinaryOp::Mod) {
        if (lhs != Type::Int || rhs != Type::Int) {
            semanticError(n.loc,
                "Operator '%' requires both operands to be 'int', got '"
                + std::string(toString(lhs)) + "' and '"
                + toString(rhs) + "'",
                "modulus is only defined for integer operands");
            return Type::Error;
        }
        return Type::Int;
    }

    // +  -  *  / 
    if (!isNumeric(lhs)) {
        semanticError(n.loc,
            "Operator '" + std::string(toString(n.op))
            + "' requires numeric operands, left operand is '"
            + toString(lhs) + "'",
            "arithmetic operators cannot be applied to 'bool'");
        return Type::Error;
    }
    if (!isNumeric(rhs)) {
        semanticError(n.loc,
            "Operator '" + std::string(toString(n.op))
            + "' requires numeric operands, right operand is '"
            + toString(rhs) + "'",
            "arithmetic operators cannot be applied to 'bool'");
        return Type::Error;
    }

    // int op int = int; any float involvement = float 
    return (lhs == Type::Float || rhs == Type::Float) ? Type::Float : Type::Int;
}

// ---- Relational: <  >  <=  >= 

Type SemanticAnalyzer::resolveRelational(BinaryExprNode& n,
                                         Type lhs, Type rhs) {
    
    if (!isNumeric(lhs) || !isNumeric(rhs)) {
        semanticError(n.loc,
            "Operator '" + std::string(toString(n.op))
            + "' requires numeric operands, got '"
            + toString(lhs) + "' and '" + toString(rhs) + "'",
            "relational operators can only compare 'int' or 'float' values");
        return Type::Error;
    }
    return Type::Bool;
}

// ---- Equality: ==  != 

Type SemanticAnalyzer::resolveEquality(BinaryExprNode& n,
                                       Type lhs, Type rhs) {
    
    if (isNumeric(lhs) && isNumeric(rhs)) return Type::Bool;
    if (lhs == Type::Bool && rhs == Type::Bool) return Type::Bool;

    semanticError(n.loc,
        "Operator '" + std::string(toString(n.op))
        + "' cannot compare '" + toString(lhs)
        + "' with '" + toString(rhs) + "'",
        "both sides must be the same kind: both numeric or both 'bool'");
    return Type::Error;
}

// ---- Logical: &&  || 

Type SemanticAnalyzer::resolveLogical(BinaryExprNode& n,
                                      Type lhs, Type rhs) {

    bool ok = true;
    if (lhs != Type::Bool) {
        semanticError(n.loc,
            "Operator '" + std::string(toString(n.op))
            + "' requires 'bool' operands, left operand is '"
            + toString(lhs) + "'",
            "use a comparison to produce a 'bool', e.g. 'x > 0'");
        ok = false;
    }
    if (rhs != Type::Bool) {
        semanticError(n.loc,
            "Operator '" + std::string(toString(n.op))
            + "' requires 'bool' operands, right operand is '"
            + toString(rhs) + "'",
            "use a comparison to produce a 'bool', e.g. 'y < 10'");
        ok = false;
    }
    return ok ? Type::Bool : Type::Error;
}

// Unary expression

void SemanticAnalyzer::visit(UnaryExprNode& n) {
    n.operand->accept(*this);
    Type t = n.operand->type;

    if (t == Type::Error) { n.type = Type::Error; return; }

    switch (n.op) {
        case UnaryOp::Neg:
            if (!isNumeric(t)) {
                semanticError(n.loc,
                    "Unary '-' requires a numeric operand, got '"
                    + std::string(toString(t)) + "'",
                    "unary negation cannot be applied to 'bool'");
                n.type = Type::Error;
                return;
            }
            n.type = t;   // -int = int, -float = float
            break;

        case UnaryOp::Not:
            if (t != Type::Bool) {
                semanticError(n.loc,
                    "Operator '!' requires a 'bool' operand, got '"
                    + std::string(toString(t)) + "'",
                    "use '!' only with boolean expressions");
                n.type = Type::Error;
                return;
            }
            n.type = Type::Bool;
            break;
    }
}

// Statements

void SemanticAnalyzer::visit(ProgramNode& n) {
    for (StmtNode* s : n.statements) s->accept(*this);
}

void SemanticAnalyzer::visit(BlockNode& n) {
    table_.enterScope();
    for (StmtNode* s : n.statements) s->accept(*this);
    table_.exitScope();
}

// ---- Declaration 

void SemanticAnalyzer::visit(DeclarationNode& n) {
    Symbol* existing = table_.lookupCurrentScope(n.name);
    if (existing) {
        semanticError(n.loc,
            "Redeclaration of variable '" + n.name
            + "' (already declared at line "
            + std::to_string(existing->declaredLine) + ")",
            "choose a different name, or remove the duplicate declaration");
        return;
    }

    Symbol sym;
    sym.name         = n.name;
    sym.type         = n.declType;
    sym.scopeLevel   = table_.currentLevel();
    sym.declaredLine = n.loc.line;
    sym.initialized  = false;
    table_.insert(sym);
}

// ---- Assignment 

void SemanticAnalyzer::visit(AssignmentNode& n) {

    Symbol* sym = table_.lookup(n.name);
    if (!sym) {
        semanticError(n.loc,
            "Undeclared variable '" + n.name + "'",
            "declare it before use, e.g. 'int " + n.name + ";'");
        n.value->accept(*this);
        return;
    }

    // Type-check the RHS
    n.value->accept(*this);
    Type rhs = n.value->type;

    if (rhs == Type::Error) return;

    Type lhs = sym->type;

    // Compatibility rules 
    bool compatible = (lhs == rhs)
                   || (lhs == Type::Float && rhs == Type::Int);

    if (!compatible) {
        std::string hint;
        if (lhs == Type::Int && rhs == Type::Float)
            hint = "assigning 'float' to 'int' loses precision; "
                   "declare '" + n.name + "' as 'float' if that is intended";
        else if (lhs == Type::Bool)
            hint = "'" + n.name + "' is 'bool'; assign 'true' or 'false'";
        else
            hint = "'" + n.name + "' is '" + toString(lhs)
                 + "'; a 'bool' value cannot be used here";

        semanticError(n.loc,
            "Cannot assign '" + std::string(toString(rhs))
            + "' to variable '" + n.name
            + "' of type '" + toString(lhs) + "'",
            hint);
        return;
    }

    sym->initialized = true;
}

// ---- If 

void SemanticAnalyzer::visit(IfNode& n) {
    n.condition->accept(*this);

    Type condType = n.condition->type;
    if (condType != Type::Error && condType != Type::Bool) {
        semanticError(n.condition->loc,
            "Condition of 'if' must be 'bool', got '"
            + std::string(toString(condType)) + "'",
            "use a comparison expression, e.g. 'x > 0'");
    }

    n.thenBranch->accept(*this);
    if (n.elseBranch) n.elseBranch->accept(*this);
}

// ---- While 

void SemanticAnalyzer::visit(WhileNode& n) {
    n.condition->accept(*this);

    Type condType = n.condition->type;
    if (condType != Type::Error && condType != Type::Bool) {
        semanticError(n.condition->loc,
            "Condition of 'while' must be 'bool', got '"
            + std::string(toString(condType)) + "'",
            "use a comparison expression, e.g. 'x > 0'");
    }

    n.body->accept(*this);
}

// ---- Print 

void SemanticAnalyzer::visit(PrintNode& n) {
    n.value->accept(*this);
}

} 
