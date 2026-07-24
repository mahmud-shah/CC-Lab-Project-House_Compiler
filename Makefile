# ============================================================================
# MiniLang Compiler - build system
#
#   make          build the compiler into build/mcc
#   make test     run the regression suite (scripts/run_tests.sh)
#   make clean    remove all generated files
#
# Generated files (Flex/Bison output, objects, the binary) live under
# build/ and are never committed (see .gitignore).
# ============================================================================

CXX      := g++
FLEX     := flex
BISON    := bison

BUILD    := build
BIN      := $(BUILD)/mcc

CXXFLAGS := -std=c++17 -Wall -Wextra -Iinclude -I$(BUILD)/gen

# --- sources ----------------------------------------------------------------
CPP_SRCS := \
    src/main.cpp \
    src/common/error_reporter.cpp \
    src/common/token_names.cpp \
    src/ast/ast.cpp \
    src/ast/ast_printer.cpp

LEXER_L      := src/lexer/lexer.l
LEXER_GEN    := $(BUILD)/gen/lex.yy.cpp
PARSER_Y     := src/parser/parser.y
PARSER_GEN_C := $(BUILD)/gen/parser.tab.cpp
PARSER_GEN_H := $(BUILD)/gen/parser.tab.hpp

CPP_OBJS   := $(CPP_SRCS:src/%.cpp=$(BUILD)/obj/%.o)
GEN_OBJS   := $(BUILD)/obj/lex.yy.o $(BUILD)/obj/parser.tab.o
OBJS       := $(CPP_OBJS) $(GEN_OBJS)

# --- top-level targets -------------------------------------------------------
.PHONY: all clean test

all: $(BIN)

$(BIN): $(OBJS)
	$(CXX) $(CXXFLAGS) $^ -o $@
	@echo "Built $(BIN)"

# --- hand-written C++ --------------------------------------------------------
# Every unit may include the Bison-generated header, so it is a prerequisite.
$(BUILD)/obj/%.o: src/%.cpp $(PARSER_GEN_H)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c $< -o $@

# --- Bison-generated parser ----------------------------------------------------
# -Wcounterexamples turns any grammar conflict into a readable derivation;
# the build treats conflicts as failures via -Werror=conflicts-sr/rr.
$(PARSER_GEN_C) $(PARSER_GEN_H) &: $(PARSER_Y)
	@mkdir -p $(dir $@)
	$(BISON) -Wall -Wcounterexamples -Werror=conflicts-sr -Werror=conflicts-rr \
	         --defines=$(PARSER_GEN_H) -o $(PARSER_GEN_C) $<

# -Wno-free-nonheap-object: silences a known GCC-13 false positive inside
# Bison 3.8's generated stack-overflow path (yyssa is only freed when it
# was actually reallocated to the heap).
$(BUILD)/obj/parser.tab.o: $(PARSER_GEN_C)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -Wno-free-nonheap-object -c $< -o $@

# --- Flex-generated scanner --------------------------------------------------
# The generated code triggers warnings we don't control; silence only those.
$(LEXER_GEN): $(LEXER_L)
	@mkdir -p $(dir $@)
	$(FLEX) -o $@ $<

$(BUILD)/obj/lex.yy.o: $(LEXER_GEN) $(PARSER_GEN_H)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -Wno-unused-function -c $< -o $@

# --- tests -------------------------------------------------------------------
test: $(BIN)
	./scripts/run_tests.sh

clean:
	rm -rf $(BUILD)
