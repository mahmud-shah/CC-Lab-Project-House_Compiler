#ifndef MINILANG_SYMBOL_TABLE_PRINTER_HPP
#define MINILANG_SYMBOL_TABLE_PRINTER_HPP

#include <ostream>

#include "minilang/symbol_table.hpp"

namespace minilang {

global)

class SymbolTablePrinter {
public:
    explicit SymbolTablePrinter(std::ostream& os) : os_(os) {}

    void print(const SymbolTable& table);

private:
    std::ostream& os_;

    void printScope(int level,
                    const std::unordered_map<std::string, Symbol>& symbols,
                    bool archived);

    static const int COL_NAME  = 12;
    static const int COL_TYPE  = 8;
    static const int COL_SCOPE = 7;
    static const int COL_LINE  = 6;
};

} 

#endif 
