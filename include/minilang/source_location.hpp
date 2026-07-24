#ifndef MINILANG_SOURCE_LOCATION_HPP
#define MINILANG_SOURCE_LOCATION_HPP

namespace minilang {

// A position in the source file. Every token, AST node, and diagnostic
// carries one of these so that all error messages can point at the exact
// line and column that caused the problem.
struct SourceLocation {
    int line = 1;
    int col  = 1;
};

} // namespace minilang

#endif // MINILANG_SOURCE_LOCATION_HPP
