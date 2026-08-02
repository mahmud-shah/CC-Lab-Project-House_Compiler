from __future__ import annotations

import re
from dataclasses import dataclass, field


TOKEN_PATTERN = re.compile(
    r"^\s*(\d+):(\d+)\s+(\S+)\s+(\S+)(?:\s+(.*?))?\s*$"
)
AST_LOCATION_PATTERN = re.compile(r"\s*\[(\d+):(\d+)\]\s*$")
SCOPE_PATTERN = re.compile(r"^Scope Level\s+(\d+)\s*(.*)$")
SYMBOL_PATTERN = re.compile(r"^(\S+)\s+(int|float|bool)\s+(\d+)\s+(\d+)\s+(yes|no)$")


@dataclass(frozen=True)
class TokenRecord:
    line: int
    column: int
    token: str
    lexeme: str
    value: str

    @property
    def location(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass
class ASTNode:
    label: str
    line: int | None = None
    column: int | None = None
    children: list["ASTNode"] = field(default_factory=list)

    @property
    def location(self) -> str:
        if self.line is None or self.column is None:
            return ""
        return f"{self.line}:{self.column}"


@dataclass(frozen=True)
class SymbolRecord:
    name: str
    type_name: str
    scope_level: int
    declared_line: int
    initialized: bool
    scope_label: str


@dataclass(frozen=True)
class TACInstruction:
    sequence: int
    kind: str
    result: str
    expression: str
    raw: str


def parse_tokens(text: str) -> tuple[TokenRecord, ...]:
    records: list[TokenRecord] = []
    for line in text.splitlines():
        match = TOKEN_PATTERN.match(line)
        if match is None:
            continue
        source_line, column, token, lexeme, value = match.groups()
        records.append(
            TokenRecord(
                line=int(source_line),
                column=int(column),
                token=token,
                lexeme=lexeme,
                value=(value or "").strip(),
            )
        )
    return tuple(records)


def parse_ast(text: str) -> tuple[ASTNode, ...]:
    roots: list[ASTNode] = []
    stack: list[tuple[int, ASTNode]] = []
    started = False

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip() == "Compilation successful.":
            continue
        if raw_line.lstrip().startswith(("Lexical Error", "Syntax Error", "Semantic Error")):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = raw_line.strip()
        if not started:
            if not content.startswith("Program"):
                continue
            started = True
        location_match = AST_LOCATION_PATTERN.search(content)
        line_number: int | None = None
        column: int | None = None
        if location_match is not None:
            line_number = int(location_match.group(1))
            column = int(location_match.group(2))
            content = content[: location_match.start()].rstrip()
        if not content:
            continue

        node = ASTNode(content, line_number, column)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if stack:
            stack[-1][1].children.append(node)
        else:
            roots.append(node)
        stack.append((indent, node))
    return tuple(roots)


def parse_symbol_table(text: str) -> tuple[SymbolRecord, ...]:
    records: list[SymbolRecord] = []
    current_scope = ""
    scope_sequence = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        scope_match = SCOPE_PATTERN.match(line)
        if scope_match is not None:
            level, description = scope_match.groups()
            scope_sequence += 1
            description = description.strip()
            if "global" in description.casefold():
                current_scope = f"Global Scope (Level {level})"
            else:
                current_scope = f"Scope {scope_sequence - 1} (Level {level})"
                if description:
                    current_scope += f" {description}"
            continue
        symbol_match = SYMBOL_PATTERN.match(line)
        if symbol_match is None:
            continue
        name, type_name, scope, declared_line, initialized = symbol_match.groups()
        records.append(
            SymbolRecord(
                name=name,
                type_name=type_name,
                scope_level=int(scope),
                declared_line=int(declared_line),
                initialized=initialized == "yes",
                scope_label=current_scope or f"Level {scope}",
            )
        )
    return tuple(records)


def parse_tac(text: str) -> tuple[TACInstruction, ...]:
    instructions: list[TACInstruction] = []
    sequence = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue
        if line == "Compilation successful.":
            continue
        if re.fullmatch(r"L\d+:", line):
            sequence += 1
            instructions.append(TACInstruction(sequence, "Label", line[:-1], "", line))
            continue

        conditional = re.fullmatch(r"ifFalse\s+(\S+)\s+goto\s+(\S+)", line)
        if conditional is not None:
            sequence += 1
            condition, label = conditional.groups()
            instructions.append(
                TACInstruction(sequence, "Conditional jump", label, condition, line)
            )
            continue

        jump = re.fullmatch(r"goto\s+(\S+)", line)
        if jump is not None:
            sequence += 1
            instructions.append(TACInstruction(sequence, "Jump", jump.group(1), "", line))
            continue

        printed = re.fullmatch(r"print\s+(.+)", line)
        if printed is not None:
            sequence += 1
            instructions.append(
                TACInstruction(sequence, "Print", "", printed.group(1), line)
            )
            continue

        assignment = re.fullmatch(r"(\S+)\s*=\s*(.+)", line)
        if assignment is not None:
            sequence += 1
            result, expression = assignment.groups()
            kind = _assignment_kind(expression)
            instructions.append(TACInstruction(sequence, kind, result, expression, line))
            continue

    return tuple(instructions)


def _assignment_kind(expression: str) -> str:
    if re.match(r"^\(float\)\s+", expression):
        return "Cast"
    if expression.startswith("!") or expression.startswith("-"):
        return "Unary"
    if re.search(r"\s(?:\+|-|\*|/|%|<=|>=|==|!=|<|>|&&|\|\|)\s", expression):
        return "Expression"
    return "Assignment"


def count_ast_nodes(nodes: tuple[ASTNode, ...]) -> int:
    return sum(1 + count_ast_nodes(tuple(node.children)) for node in nodes)
