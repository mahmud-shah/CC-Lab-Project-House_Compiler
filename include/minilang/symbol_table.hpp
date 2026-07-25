#ifndef MINILANG_SYMBOL_TABLE_HPP
#define MINILANG_SYMBOL_TABLE_HPP

#include <string>
#include <unordered_map>
#include <vector>

#include "minilang/type.hpp"

namespace minilang {

struct Symbol {
    std::string name;
    Type        type;
    int         scopeLevel;   
    int         declaredLine;
    bool        initialized = false;
};


struct ScopeRecord {
    int                                     level;
    std::unordered_map<std::string, Symbol> symbols;
};

class SymbolTable {
public:
    SymbolTable();

    void enterScope();

    void exitScope();

    int currentLevel() const;

    bool insert(const Symbol& sym);

    Symbol* lookup(const std::string& name);

    Symbol* lookupCurrentScope(const std::string& name);

    const std::vector<std::unordered_map<std::string, Symbol>>&
    activeScopes() const { return scopes_; }

    const std::vector<ScopeRecord>& archive() const { return archive_; }

    int totalSymbols() const;

private:

    std::vector<std::unordered_map<std::string, Symbol>> scopes_;

    std::vector<ScopeRecord> archive_;

    int currentLevel_ = 0;
};

} 

#endif