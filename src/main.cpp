#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

#include "minilang/ast.hpp"
#include "minilang/ast_printer.hpp"
#include "minilang/error_reporter.hpp"
#include "minilang/lexer.hpp"
#include "minilang/semantic_analyzer.hpp"
#include "minilang/symbol_table_printer.hpp"
#include "parser.tab.hpp"

namespace {

struct Options {
    std::string sourcePath;
    bool tokens = false;
    bool ast    = false;
    bool symtab = false;
};

void printUsage(const char* prog) {
    std::cerr
        << "MiniLang Compiler (mcc)\n"
        << "Usage: " << prog << " <source-file> [options]\n\n"
        << "Options:\n"
        << "  --tokens     print the token stream produced by the lexer\n"
        << "  --ast        print the abstract syntax tree after parsing\n"
        << "  --symtab     print the symbol table after semantic analysis\n"
        << "  --help       show this message\n";
}

int runTokenDump(minilang::ErrorReporter& reporter) {
    std::cout << std::left
              << std::setw(10) << "LOC"
              << std::setw(16) << "TOKEN"
              << std::setw(16) << "LEXEME"
              << "VALUE\n"
              << std::string(52, '-') << "\n";

    long tokenCount = 0;
    int  kind;
    while ((kind = yylex()) != 0) {
        ++tokenCount;
        std::string loc = std::to_string(minilang::ml_token_loc.line) + ":"
                        + std::to_string(minilang::ml_token_loc.col);

        std::cout << std::left
                  << std::setw(10) << loc
                  << std::setw(16) << minilang::tokenName(kind)
                  << std::setw(16) << yytext;

        switch (kind) {
            case TOK_INT_LIT:   std::cout << yylval.ival; break;
            case TOK_FLOAT_LIT: std::cout << yylval.fval; break;
            case TOK_KW_TRUE:
            case TOK_KW_FALSE:  std::cout << (yylval.bval ? "true" : "false"); break;
            case TOK_IDENT:
                std::cout << "\"" << yylval.sval << "\"";
                std::free(yylval.sval);
                break;
            default: break;
        }
        std::cout << "\n";
    }

    std::cout << std::string(52, '-') << "\n"
              << tokenCount << " token(s), "
              << reporter.errorCount() << " lexical error(s)\n";

    if (!reporter.diagnostics().empty()) {
        std::cout << "\n";
        reporter.printAll(std::cout);
    }
    return reporter.hasErrors() ? 1 : 0;
}

int runCompile(const Options& opts, minilang::ErrorReporter& reporter) {

    minilang::ProgramNode* ast = nullptr;
    yyparse(&ast);

    if (opts.ast && ast != nullptr) {
        minilang::ASTPrinter printer(std::cout);
        printer.print(*ast);
        std::cout << "\n";
    }

    minilang::SemanticAnalyzer semantic(reporter);
    bool semanticOk = false;

    if (ast != nullptr && !reporter.hasErrors()) {
        semanticOk = semantic.analyze(*ast);
    }


    if (opts.symtab && ast != nullptr) {
        minilang::SymbolTablePrinter stp(std::cout);
        stp.print(semantic.symbolTable());
    }

    // ---- Diagnostics 
    int exitCode = 0;
    if (reporter.hasErrors()) {
        reporter.printAll(std::cerr);
        std::cerr << reporter.errorCount() << " error(s) found.\n";
        exitCode = 1;
    } else {
        std::cout << "Compilation successful.\n";
        (void)semanticOk; 
    }

    delete ast;
    return exitCode;
}

} 

int main(int argc, char** argv) {
    Options opts;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if      (arg == "--tokens") opts.tokens = true;
        else if (arg == "--ast")    opts.ast    = true;
        else if (arg == "--symtab") opts.symtab = true;
        else if (arg == "--help")   { printUsage(argv[0]); return 0; }
        else if (!arg.empty() && arg[0] == '-') {
            std::cerr << "mcc: unknown option '" << arg << "'\n";
            printUsage(argv[0]);
            return 2;
        } else if (opts.sourcePath.empty()) {
            opts.sourcePath = arg;
        } else {
            std::cerr << "mcc: multiple input files\n";
            return 2;
        }
    }

    if (opts.sourcePath.empty()) {
        std::cerr << "mcc: no input file\n";
        printUsage(argv[0]);
        return 2;
    }

    std::FILE* input = std::fopen(opts.sourcePath.c_str(), "r");
    if (!input) {
        std::cerr << "mcc: cannot open '" << opts.sourcePath << "'\n";
        return 2;
    }

    minilang::ErrorReporter reporter;
    minilang::ErrorReporter::setGlobal(&reporter);
    minilang::lexerInit(input);

    int exitCode = opts.tokens ? runTokenDump(reporter)
                               : runCompile(opts, reporter);

    std::fclose(input);
    return exitCode;
}
