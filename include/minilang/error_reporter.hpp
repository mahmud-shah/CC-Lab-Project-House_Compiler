#ifndef MINILANG_ERROR_REPORTER_HPP
#define MINILANG_ERROR_REPORTER_HPP

#include <cstddef>
#include <ostream>
#include <string>
#include <vector>

#include "minilang/source_location.hpp"

namespace minilang {

// The three diagnostic categories required by the Project Manual, plus
// Warning for non-fatal advisories (e.g. constant division by zero).
enum class ErrorCategory {
    Lexical,
    Syntax,
    Semantic,
    Warning
};

struct Diagnostic {
    ErrorCategory  category;
    SourceLocation loc;
    std::string    message; // what happened, mentioning the offending token
    std::string    hint;    // optional "possible fix" suggestion
};

// Collects diagnostics from every compiler phase instead of aborting on
// the first problem. This is what lets the compiler satisfy the manual's
// requirement to "never stop after the first semantic error": each phase
// reports into this object and keeps going; the driver prints everything
// at the end and decides the exit code.
//
// A single instance is created by the driver and handed to each phase.
// The Flex-generated lexer is plain C-style code, so it reaches the
// reporter through the global() accessor set up by the driver.
class ErrorReporter {
public:
    void report(ErrorCategory category, SourceLocation loc,
                std::string message, std::string hint = "");

    // Errors only (warnings excluded) - drives the process exit code and
    // the decision to suppress TAC output.
    bool        hasErrors()   const;
    std::size_t errorCount()  const;
    std::size_t warningCount() const;

    std::size_t countOf(ErrorCategory category) const;

    // Prints all diagnostics in the order they were produced, in the
    // uniform format:
    //   <Category> Error [line L, col C]: <message>
    //     --> hint: <hint>
    void printAll(std::ostream& os) const;

    const std::vector<Diagnostic>& diagnostics() const { return diagnostics_; }

    // Global access point for C-style callers (the Flex lexer).
    // The driver must call setGlobal() before scanning begins.
    static ErrorReporter& global();
    static void           setGlobal(ErrorReporter* reporter);

private:
    std::vector<Diagnostic> diagnostics_;
};

} // namespace minilang

#endif // MINILANG_ERROR_REPORTER_HPP
