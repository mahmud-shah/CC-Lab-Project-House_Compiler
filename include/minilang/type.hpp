#ifndef MINILANG_TYPE_HPP
#define MINILANG_TYPE_HPP

namespace minilang {

// The MiniLang type system (Project Manual §5.1): exactly three concrete
// types. Two extra internal values support the semantic analyzer:
//
//   Unresolved - an expression node that has not been type-checked yet
//   Error      - a node whose subtree already produced a semantic error;
//                propagating Error suppresses cascading duplicate messages
enum class Type {
    Int,
    Float,
    Bool,
    Unresolved,
    Error
};

inline const char* toString(Type t) {
    switch (t) {
        case Type::Int:        return "int";
        case Type::Float:      return "float";
        case Type::Bool:       return "bool";
        case Type::Unresolved: return "<unresolved>";
        case Type::Error:      return "<error>";
    }
    return "<invalid>";
}

// True for the two numeric types (int/float). Used by the semantic rules
// for arithmetic and relational operators.
inline bool isNumeric(Type t) {
    return t == Type::Int || t == Type::Float;
}

} // namespace minilang

#endif // MINILANG_TYPE_HPP
