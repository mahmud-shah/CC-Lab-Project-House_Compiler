#include "minilang/tac.hpp"

namespace minilang {

// ---- TACProgram 

void TACProgram::emit(TACInstr instr) {
    instrs_.push_back(std::move(instr));
}

void TACProgram::print(std::ostream& os,
                       const std::string& sourceFile) const {
    if (!sourceFile.empty())
        os << "; === Three Address Code: " << sourceFile << " ===\n\n";

    for (const auto& instr : instrs_) {
        if (instr.op == TACInstr::Op::Label)
            os << instr.toString() << "\n";
        else
            os << "    " << instr.toString() << "\n";
    }
}

// ---- TACInstr::toString 

std::string TACInstr::toString() const {
    switch (op) {

        case Op::AssignInt:
        case Op::AssignFloat:
        case Op::AssignBool:   return result + " = " + arg1;
        case Op::Copy:         return result + " = " + arg1;
        case Op::CastFloat:    return result + " = (float) " + arg1;

        // Binary arithmetic
        case Op::Add:          return result + " = " + arg1 + " + " + arg2;
        case Op::Sub:          return result + " = " + arg1 + " - " + arg2;
        case Op::Mul:          return result + " = " + arg1 + " * " + arg2;
        case Op::Div:          return result + " = " + arg1 + " / " + arg2;
        case Op::Mod:          return result + " = " + arg1 + " % " + arg2;

        // Binary relational
        case Op::Lt:           return result + " = " + arg1 + " < "  + arg2;
        case Op::Gt:           return result + " = " + arg1 + " > "  + arg2;
        case Op::Le:           return result + " = " + arg1 + " <= " + arg2;
        case Op::Ge:           return result + " = " + arg1 + " >= " + arg2;
        case Op::Eq:           return result + " = " + arg1 + " == " + arg2;
        case Op::Neq:          return result + " = " + arg1 + " != " + arg2;

        // Unary
        case Op::Neg:          return result + " = -" + arg1;
        case Op::Not:          return result + " = !" + arg1;

        // Control flow
        case Op::Label:        return result + ":";
        case Op::Goto:         return "goto " + arg1;
        case Op::IfFalse:      return "ifFalse " + arg1 + " goto " + arg2;
        case Op::IfTrue:       return "ifTrue "  + arg1 + " goto " + arg2;

        // I/O
        case Op::Print:        return "print " + arg1;
    }
    return "; <unknown instruction>";
}

} 
