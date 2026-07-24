// ============================================================================
// mcc - the MiniLang compiler driver
//
// Owns the compilation pipeline; each project phase adds one stage:
//
//     source --> Lexer (Flex) --> Parser (Bison) --> AST
//                                                     |
//                        [next phases: semantic analysis, TAC]
//
// Modes:
//     mcc <file>            compile (currently: lex + parse, report errors)
//     mcc <file> --tokens   dump the token stream only (scanner in isolation)
//     mcc <file> --ast      compile and print the abstract syntax tree
//
// Exit codes: 0 = clean, 1 = compilation errors, 2 = usage/IO problem.
// ============================================================================

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>

#include "minilang/ast.hpp"
#include "minilang/ast_printer.hpp"
#include "minilang/error_reporter.hpp"
#include "minilang/lexer.hpp"
#include "parser.tab.hpp"

namespace {

struct Options {
    std::string sourcePath;
    bool tokens = false;
    bool ast    = false;
};

void printUsage(const char* prog) {
    std::cerr
        << "MiniLang Compiler (mcc)\n"
        << "Usage: " << prog << " <source-file> [options]\n\n"
        << "Options:\n"
        << "  --tokens     print the token stream produced by the lexer\n"
        << "  --ast        print the abstract syntax tree after parsing\n"
        << "  --help       show this message\n";
}

// Scanner-in-isolation mode: prints one row per token. Lexical errors are
// collected and printed afterwards, so a bad character never hides the
// tokens that follow it.
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

        std::string loc = std::to_string(minilang::ml_token_loc.line) + ":" +
                          std::to_string(minilang::ml_token_loc.col);
        std::cout << std::left
                  << std::setw(10) << loc
                  << std::setw(16) << minilang::tokenName(kind)
                  << std::setw(16) << yytext;

        switch (kind) {
            case TOK_INT_LIT:   std::cout << yylval.ival; break;
            case TOK_FLOAT_LIT: std::cout << yylval.fval; break;
            case TOK_KW_TRUE:
            case TOK_KW_FALSE:  std::cout << (yylval.bval ? "true" : "false");
                                break;
            case TOK_IDENT:
                std::cout << "\"" << yylval.sval << "\"";
                std::free(yylval.sval); // dump mode is the value's consumer
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

// Full pipeline (current phases): parse the file - the parser pulls tokens
// from the lexer itself - then report every collected diagnostic.
int runCompile(const Options& opts, minilang::ErrorReporter& reporter) {
    minilang::ProgramNode* ast = nullptr;
    yyparse(&ast);

    if (opts.ast && ast != nullptr) {
        minilang::ASTPrinter printer(std::cout);
        printer.print(*ast);
    }

    int exitCode = 0;
    if (reporter.hasErrors()) {
        reporter.printAll(std::cerr);
        std::cerr << reporter.errorCount() << " error(s) found.\n";
        exitCode = 1;
    } else {
        std::cout << "Compilation successful: lexical and syntax analysis "
                  << "completed with no errors.\n";
    }

    delete ast;
    return exitCode;
}

} // namespace

int main(int argc, char** argv) {
    Options opts;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--tokens") {
            opts.tokens = true;
        } else if (arg == "--ast") {
            opts.ast = true;
        } else if (arg == "--help") {
            printUsage(argv[0]);
            return 0;
        } else if (!arg.empty() && arg[0] == '-') {
            std::cerr << "mcc: unknown option '" << arg << "'\n";
            printUsage(argv[0]);
            return 2;
        } else if (opts.sourcePath.empty()) {
            opts.sourcePath = arg;
        } else {
            std::cerr << "mcc: multiple input files given ('" << opts.sourcePath
                      << "' and '" << arg << "')\n";
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
