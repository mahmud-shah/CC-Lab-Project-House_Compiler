#include "minilang/symbol_table.hpp"

#include <cassert>
#include <stdexcept>

namespace minilang {

SymbolTable::SymbolTable() {
    scopes_.emplace_back();
}

void SymbolTable::enterScope() {
    ++currentLevel_;
    scopes_.emplace_back();
}

void SymbolTable::exitScope() {
    assert(!scopes_.empty() && "exitScope() called with no open scope");
    assert(currentLevel_ > 0 && "cannot exit the global scope");

    archive_.push_back(ScopeRecord{currentLevel_,
                                   std::move(scopes_.back())});
    scopes_.pop_back();
    --currentLevel_;
}

int SymbolTable::currentLevel() const {
    return currentLevel_;
}

bool SymbolTable::insert(const Symbol& sym) {
    assert(!scopes_.empty());

    auto& current = scopes_.back();

    if (current.count(sym.name)) {
        return false;
    }

    current.emplace(sym.name, sym);
    return true;
}

Symbol* SymbolTable::lookup(const std::string& name) {
    
    for (auto it = scopes_.rbegin(); it != scopes_.rend(); ++it) {
        auto found = it->find(name);
        if (found != it->end()) {
            return &found->second;
        }
    }
    return nullptr;
}

Symbol* SymbolTable::lookupCurrentScope(const std::string& name) {
    assert(!scopes_.empty());
    auto& current = scopes_.back();
    auto  found   = current.find(name);
    return found != current.end() ? &found->second : nullptr;
}

int SymbolTable::totalSymbols() const {
    int total = 0;
    for (const auto& scope : scopes_)
        total += static_cast<int>(scope.size());
    for (const auto& record : archive_)
        total += static_cast<int>(record.symbols.size());
    return total;
}

}