CXX      := g++
FLEX     := flex
BISON    := bison

BUILD    := build
BIN      := $(BUILD)/mcc

CXXFLAGS := -std=c++17 -Wall -Wextra -Iinclude -I$(BUILD)/gen

CPP_SRCS := \
    src/main.cpp \
    src/common/error_reporter.cpp \
    src/common/token_names.cpp \
    src/ast/ast.cpp \
    src/ast/ast_printer.cpp \
    src/symbol_table/symbol_table.cpp \
    src/symbol_table/symbol_table_printer.cpp\
	src/semantic/semantic_analyzer.cpp\
	src/tac/tac.cpp\
	src/tac/tac_generator.cpp 

LEXER_L      := src/lexer/lexer.l
LEXER_GEN    := $(BUILD)/gen/lex.yy.cpp
PARSER_Y     := src/parser/parser.y
PARSER_GEN_C := $(BUILD)/gen/parser.tab.cpp
PARSER_GEN_H := $(BUILD)/gen/parser.tab.hpp

CPP_OBJS   := $(CPP_SRCS:src/%.cpp=$(BUILD)/obj/%.o)
GEN_OBJS   := $(BUILD)/obj/lex.yy.o $(BUILD)/obj/parser.tab.o
OBJS       := $(CPP_OBJS) $(GEN_OBJS)

.PHONY: all clean test

all: $(BIN)

$(BIN): $(OBJS)
	$(CXX) $(CXXFLAGS) $^ -o $@
	@echo "Built $(BIN)"


$(BUILD)/obj/%.o: src/%.cpp $(PARSER_GEN_H)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(PARSER_GEN_C) $(PARSER_GEN_H) &: $(PARSER_Y)
	@mkdir -p $(dir $@)
	$(BISON) -Wall -Wcounterexamples -Werror=conflicts-sr -Werror=conflicts-rr \
	         --defines=$(PARSER_GEN_H) -o $(PARSER_GEN_C) $<

$(BUILD)/obj/parser.tab.o: $(PARSER_GEN_C)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -Wno-free-nonheap-object -c $< -o $@

$(LEXER_GEN): $(LEXER_L)
	@mkdir -p $(dir $@)
	$(FLEX) -o $@ $<

$(BUILD)/obj/lex.yy.o: $(LEXER_GEN) $(PARSER_GEN_H)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -Wno-unused-function -c $< -o $@

test: $(BIN)
	./scripts/run_tests.sh

clean:
	rm -rf $(BUILD)
