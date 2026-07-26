#ifndef MINILANG_TAC_HPP
#define MINILANG_TAC_HPP

#include <ostream>
#include <string>
#include <vector>

namespace minilang {

struct TACInstr {
    enum class Op {
        // Literal assignments
        AssignInt,
        AssignFloat,
        AssignBool,

        // Copy / cast
        Copy,
        CastFloat,

        // Binary arithmetic
        Add, Sub, Mul, Div, Mod,

        // Binary relational (result is a bool-valued temp)
        Lt, Gt, Le, Ge, Eq, Neq,

        // Unary
        Neg,
        Not,

        // Control flow
        Label,
        Goto,
        IfFalse,
        IfTrue,

        // I/O
        Print,
    };

    Op          op;
    std::string result;
    std::string arg1;
    std::string arg2;

    std::string toString() const;
};

// Ordered list of TAC instructions for a whole program.
class TACProgram {
public:
    void emit(TACInstr instr);

    void print(std::ostream& os,
               const std::string& sourceFile = "") const;

    const std::vector<TACInstr>& instructions() const { return instrs_; }
    bool empty() const { return instrs_.empty(); }

private:
    std::vector<TACInstr> instrs_;
};

} 

#endif 
