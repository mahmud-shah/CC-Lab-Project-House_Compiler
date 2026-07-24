#include "minilang/error_reporter.hpp"

#include <cassert>

namespace minilang {

namespace {
const char* categoryLabel(ErrorCategory c) {
    switch (c) {
        case ErrorCategory::Lexical:  return "Lexical Error";
        case ErrorCategory::Syntax:   return "Syntax Error";
        case ErrorCategory::Semantic: return "Semantic Error";
        case ErrorCategory::Warning:  return "Warning";
    }
    return "Error";
}

ErrorReporter* g_reporter = nullptr;
} // namespace

void ErrorReporter::report(ErrorCategory category, SourceLocation loc,
                           std::string message, std::string hint) {
    diagnostics_.push_back(
        Diagnostic{category, loc, std::move(message), std::move(hint)});
}

bool ErrorReporter::hasErrors() const {
    return errorCount() > 0;
}

std::size_t ErrorReporter::errorCount() const {
    std::size_t n = 0;
    for (const auto& d : diagnostics_)
        if (d.category != ErrorCategory::Warning) ++n;
    return n;
}

std::size_t ErrorReporter::warningCount() const {
    return countOf(ErrorCategory::Warning);
}

std::size_t ErrorReporter::countOf(ErrorCategory category) const {
    std::size_t n = 0;
    for (const auto& d : diagnostics_)
        if (d.category == category) ++n;
    return n;
}

void ErrorReporter::printAll(std::ostream& os) const {
    for (const auto& d : diagnostics_) {
        os << categoryLabel(d.category)
           << " [line " << d.loc.line << ", col " << d.loc.col << "]: "
           << d.message << "\n";
        if (!d.hint.empty())
            os << "  --> hint: " << d.hint << "\n";
    }
}

ErrorReporter& ErrorReporter::global() {
    assert(g_reporter != nullptr &&
           "ErrorReporter::setGlobal() must be called by the driver first");
    return *g_reporter;
}

void ErrorReporter::setGlobal(ErrorReporter* reporter) {
    g_reporter = reporter;
}

} // namespace minilang
