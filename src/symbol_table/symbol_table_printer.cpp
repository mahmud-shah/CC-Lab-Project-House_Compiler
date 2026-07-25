#include "minilang/symbol_table_printer.hpp"

#include <algorithm>
#include <iomanip>
#include <string>
#include <vector>

namespace minilang {

void SymbolTablePrinter::print(const SymbolTable& table) {
    os_ << "\n=== Symbol Table ===\n";

    const auto& active = table.activeScopes();
    for (std::size_t i = 0; i < active.size(); ++i) {
        printScope(static_cast<int>(i), active[i], false);
    }

    for (const auto& record : table.archive()) {
        printScope(record.level, record.symbols, true);
    }

    os_ << "\nTotal symbols declared: " << table.totalSymbols() << "\n";
}

void SymbolTablePrinter::printScope(
        int level,
        const std::unordered_map<std::string, Symbol>& symbols,
        bool archived) {

    os_ << "\nScope Level " << level;
    if (level == 0) os_ << " (global)";
    if (archived)   os_ << " [archived]";
    os_ << "\n";
    os_ << std::string(50, '-') << "\n";

    if (symbols.empty()) {
        os_ << "  (empty)\n";
        return;
    }

    os_ << std::left
        << std::setw(COL_NAME)  << "NAME"
        << std::setw(COL_TYPE)  << "TYPE"
        << std::setw(COL_SCOPE) << "SCOPE"
        << std::setw(COL_LINE)  << "LINE"
        << "INITIALIZED\n";

    std::vector<const Symbol*> sorted;
    sorted.reserve(symbols.size());
    for (const auto& kv : symbols) sorted.push_back(&kv.second);
    std::sort(sorted.begin(), sorted.end(),
              [](const Symbol* a, const Symbol* b) {
                  return a->declaredLine < b->declaredLine;
              });

    for (const Symbol* sym : sorted) {
        os_ << std::left
            << std::setw(COL_NAME)  << sym->name
            << std::setw(COL_TYPE)  << toString(sym->type)
            << std::setw(COL_SCOPE) << sym->scopeLevel
            << std::setw(COL_LINE)  << sym->declaredLine
            << (sym->initialized ? "yes" : "no") << "\n";
    }
}

} 
