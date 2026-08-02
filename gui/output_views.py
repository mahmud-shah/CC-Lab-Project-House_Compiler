from __future__ import annotations

import tkinter as tk
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .output_parsers import (
    ASTNode,
    SymbolRecord,
    TACInstruction,
    TokenRecord,
    count_ast_nodes,
    parse_ast,
    parse_symbol_table,
    parse_tac,
    parse_tokens,
)
from .theme import COLORS, ThemeFonts


class StructuredOutputView(ttk.Frame):
    """Base surface that preserves raw output alongside a structured view."""

    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        *,
        save_extension: str = ".txt",
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=6)
        self.fonts = fonts
        self.save_extension = save_extension
        self._raw_text = ""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.actions = ttk.Frame(self, style="Surface.TFrame")
        self.actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.actions.columnconfigure(20, weight=1)
        ttk.Button(
            self.actions,
            text="Copy Raw",
            command=self.copy_all,
            style="Toolbar.TButton",
        ).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(
            self.actions,
            text="Save Raw...",
            command=self.save_as,
            style="Toolbar.TButton",
        ).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(
            self.actions,
            text="View Raw",
            command=self.show_raw,
            style="Toolbar.TButton",
        ).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(
            self.actions,
            text="Clear",
            command=self.clear,
            style="Toolbar.TButton",
        ).grid(row=0, column=3)
        self.summary = tk.StringVar(value="No output")
        ttk.Label(
            self.actions, textvariable=self.summary, style="Muted.TLabel"
        ).grid(row=0, column=20, sticky="e", padx=(10, 4))

        self.notice = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self.notice,
            style="Muted.TLabel",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(5, 0))

    def get_content(self) -> str:
        return self._raw_text

    def copy_all(self) -> None:
        if not self._raw_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self._raw_text)

    def save_as(self) -> None:
        if not self._raw_text:
            messagebox.showinfo("Nothing to save", "This compiler output is empty.")
            return
        selected = filedialog.asksaveasfilename(
            title="Save raw compiler output",
            defaultextension=self.save_extension,
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            Path(selected).write_text(self._raw_text, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save output:\n\n{exc}")

    def show_raw(self) -> None:
        if not self._raw_text:
            messagebox.showinfo("No raw output", "This compiler output is empty.")
            return
        window = tk.Toplevel(self)
        window.title("Raw Compiler Output")
        window.geometry("900x600")
        window.configure(background=COLORS.surface)
        frame = ttk.Frame(window, style="Surface.TFrame", padding=8)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(
            frame,
            wrap="none",
            background=COLORS.editor,
            foreground=COLORS.text_soft,
            selectbackground=COLORS.selection,
            relief="flat",
            padx=12,
            pady=10,
            font=(self.fonts.mono, 10),
        )
        vertical = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        text.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        text.insert("1.0", self._raw_text)
        text.configure(state="disabled")

    def clear(self) -> None:
        raise NotImplementedError

    def focus_view(self) -> None:
        raise NotImplementedError


class TokenTableView(StructuredOutputView):
    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        on_navigate: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__(parent, fonts)
        self.records: tuple[TokenRecord, ...] = ()
        self.on_navigate = on_navigate
        self._tree_records: dict[str, TokenRecord] = {}
        self.filter_value = tk.StringVar()

        ttk.Label(self.actions, text="Filter", style="Muted.TLabel").grid(
            row=0, column=5, padx=(14, 5)
        )
        filter_entry = ttk.Entry(
            self.actions, textvariable=self.filter_value, width=22
        )
        filter_entry.grid(row=0, column=6)
        self.filter_value.trace_add("write", lambda *_args: self._populate())

        frame = ttk.Frame(self, style="Surface.TFrame")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("location", "token", "lexeme", "value")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        definitions = {
            "location": ("Location", 90, "center"),
            "token": ("Token", 190, "w"),
            "lexeme": ("Lexeme", 180, "w"),
            "value": ("Value", 240, "w"),
        }
        for name, (caption, width, anchor) in definitions.items():
            self.tree.heading(name, text=caption)
            self.tree.column(name, width=width, anchor=anchor, stretch=name == "value")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("keyword", foreground=COLORS.accent)
        self.tree.tag_configure("literal", foreground=COLORS.warning)
        self.tree.tag_configure("identifier", foreground=COLORS.text)
        self.tree.tag_configure("operator", foreground=COLORS.violet)
        self.tree.bind("<Double-1>", self._activate_selected)
        self.tree.bind("<Return>", self._activate_selected)

    def set_content(self, content: str, _tag: str | None = None) -> None:
        self._raw_text = content
        self.records = parse_tokens(content)
        self._populate()

    def clear(self) -> None:
        self._raw_text = ""
        self.records = ()
        self._tree_records.clear()
        self.tree.delete(*self.tree.get_children())
        self.summary.set("No token output")
        self.notice.set("")

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._tree_records.clear()
        query = self.filter_value.get().strip().casefold()
        visible = [
            record
            for record in self.records
            if not query
            or query in record.token.casefold()
            or query in record.lexeme.casefold()
            or query in record.value.casefold()
            or query in record.location
        ]
        for record in visible:
            category = self._category(record.token)
            item = self.tree.insert(
                "",
                "end",
                values=(record.location, record.token, record.lexeme, record.value),
                tags=(category,),
            )
            self._tree_records[item] = record
        self.summary.set(f"{len(visible)} of {len(self.records)} tokens")
        self.notice.set(
            "Structured token stream from the Flex scanner"
            if self.records
            else self._empty_notice("No token rows were found")
        )

    @staticmethod
    def _category(token: str) -> str:
        if token.startswith("KEYWORD"):
            return "keyword"
        if token in {"INT_LITERAL", "FLOAT_LITERAL", "BOOL_LITERAL"}:
            return "literal"
        if token == "IDENTIFIER":
            return "identifier"
        return "operator"

    def _empty_notice(self, fallback: str) -> str:
        first = self._raw_text.strip().splitlines()
        return first[0] if first else fallback

    def _activate_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        selection = self.tree.selection()
        if not selection or self.on_navigate is None:
            return
        record = self._tree_records.get(selection[0])
        if record is not None:
            self.on_navigate(record.line, record.column)


class ASTTreeView(StructuredOutputView):
    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        on_navigate: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__(parent, fonts)
        self.nodes: tuple[ASTNode, ...] = ()
        self.on_navigate = on_navigate
        self._tree_nodes: dict[str, ASTNode] = {}
        ttk.Button(
            self.actions,
            text="Expand All",
            command=lambda: self._set_expanded(True),
            style="Toolbar.TButton",
        ).grid(row=0, column=5, padx=(14, 5))
        ttk.Button(
            self.actions,
            text="Collapse All",
            command=lambda: self._set_expanded(False),
            style="Toolbar.TButton",
        ).grid(row=0, column=6)

        frame = ttk.Frame(self, style="Surface.TFrame")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, columns=("location",), show="tree headings")
        self.tree.heading("#0", text="AST Node")
        self.tree.heading("location", text="Source Location")
        self.tree.column("#0", width=560, minwidth=260, stretch=True)
        self.tree.column("location", width=130, anchor="center", stretch=False)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("root", foreground=COLORS.accent)
        self.tree.tag_configure("control", foreground=COLORS.violet)
        self.tree.tag_configure("leaf", foreground=COLORS.text_soft)
        self.tree.bind("<Double-1>", self._activate_selected)
        self.tree.bind("<Return>", self._activate_selected)

    def set_content(self, content: str, _tag: str | None = None) -> None:
        self._raw_text = content
        self.nodes = parse_ast(content)
        self.tree.delete(*self.tree.get_children())
        self._tree_nodes.clear()
        for node in self.nodes:
            self._insert_node("", node, depth=0)
        total = count_ast_nodes(self.nodes)
        self.summary.set(f"{total} AST nodes")
        self.notice.set(
            "Hierarchical abstract syntax tree"
            if total
            else self._empty_notice("No AST nodes were found")
        )

    def clear(self) -> None:
        self._raw_text = ""
        self.nodes = ()
        self._tree_nodes.clear()
        self.tree.delete(*self.tree.get_children())
        self.summary.set("No AST output")
        self.notice.set("")

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _insert_node(self, parent: str, node: ASTNode, depth: int) -> None:
        if depth == 0:
            tag = "root"
        elif node.label in {"Condition", "Then", "Else"} or node.label.startswith(
            ("If", "While", "Block")
        ):
            tag = "control"
        else:
            tag = "leaf"
        item = self.tree.insert(
            parent,
            "end",
            text=node.label,
            values=(node.location,),
            open=depth < 2,
            tags=(tag,),
        )
        self._tree_nodes[item] = node
        for child in node.children:
            self._insert_node(item, child, depth + 1)

    def _set_expanded(self, expanded: bool) -> None:
        def visit(item: str) -> None:
            self.tree.item(item, open=expanded)
            for child in self.tree.get_children(item):
                visit(child)

        for root in self.tree.get_children():
            visit(root)

    def _empty_notice(self, fallback: str) -> str:
        first = self._raw_text.strip().splitlines()
        return first[0] if first else fallback

    def _activate_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        selection = self.tree.selection()
        if not selection or self.on_navigate is None:
            return
        node = self._tree_nodes.get(selection[0])
        if node is not None and node.line is not None and node.column is not None:
            self.on_navigate(node.line, node.column)


class SymbolTableView(StructuredOutputView):
    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        on_navigate: Callable[[int, int], None] | None = None,
    ) -> None:
        super().__init__(parent, fonts)
        self.records: tuple[SymbolRecord, ...] = ()
        self.on_navigate = on_navigate
        self._tree_records: dict[str, SymbolRecord] = {}
        self.filter_value = tk.StringVar()
        ttk.Label(self.actions, text="Filter", style="Muted.TLabel").grid(
            row=0, column=5, padx=(14, 5)
        )
        ttk.Entry(self.actions, textvariable=self.filter_value, width=22).grid(
            row=0, column=6
        )
        self.filter_value.trace_add("write", lambda *_args: self._populate())

        frame = ttk.Frame(self, style="Surface.TFrame")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("name", "type", "scope", "line", "initialized")
        self.tree = ttk.Treeview(frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Scope Group")
        self.tree.column("#0", width=210, minwidth=130, stretch=True)
        definitions = {
            "name": ("Identifier", 190),
            "type": ("Type", 90),
            "scope": ("Scope", 80),
            "line": ("Declared Line", 110),
            "initialized": ("Initialized", 100),
        }
        for name, (caption, width) in definitions.items():
            self.tree.heading(name, text=caption)
            self.tree.column(name, width=width, anchor="center", stretch=name == "name")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("scope", foreground=COLORS.accent)
        self.tree.tag_configure("initialized", foreground=COLORS.success)
        self.tree.tag_configure("uninitialized", foreground=COLORS.warning)
        self.tree.bind("<Double-1>", self._activate_selected)
        self.tree.bind("<Return>", self._activate_selected)

    def set_content(self, content: str, _tag: str | None = None) -> None:
        self._raw_text = content
        self.records = parse_symbol_table(content)
        self._populate()

    def clear(self) -> None:
        self._raw_text = ""
        self.records = ()
        self._tree_records.clear()
        self.tree.delete(*self.tree.get_children())
        self.summary.set("No symbol-table output")
        self.notice.set("")

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._tree_records.clear()
        query = self.filter_value.get().strip().casefold()
        visible = [
            record
            for record in self.records
            if not query
            or query in record.name.casefold()
            or query in record.type_name.casefold()
            or query in record.scope_label.casefold()
        ]
        groups: OrderedDict[str, list[SymbolRecord]] = OrderedDict()
        for record in visible:
            groups.setdefault(record.scope_label, []).append(record)
        for scope_label, records in groups.items():
            parent = self.tree.insert(
                "", "end", text=scope_label, open=True, tags=("scope",)
            )
            for record in records:
                item = self.tree.insert(
                    parent,
                    "end",
                    text="",
                    values=(
                        record.name,
                        record.type_name,
                        record.scope_level,
                        record.declared_line,
                        "yes" if record.initialized else "no",
                    ),
                    tags=("initialized" if record.initialized else "uninitialized",),
                )
                self._tree_records[item] = record
        self.summary.set(f"{len(visible)} of {len(self.records)} symbols")
        self.notice.set(
            f"{len(groups)} scope group{'s' if len(groups) != 1 else ''}"
            if self.records
            else self._empty_notice("No symbol records were found")
        )

    def _empty_notice(self, fallback: str) -> str:
        first = self._raw_text.strip().splitlines()
        return first[0] if first else fallback

    def _activate_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        selection = self.tree.selection()
        if not selection or self.on_navigate is None:
            return
        record = self._tree_records.get(selection[0])
        if record is not None:
            self.on_navigate(record.declared_line, 1)


class TACTableView(StructuredOutputView):
    def __init__(self, parent: tk.Misc, fonts: ThemeFonts) -> None:
        super().__init__(parent, fonts, save_extension=".tac")
        self.instructions: tuple[TACInstruction, ...] = ()

        frame = ttk.Frame(self, style="Surface.TFrame")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("sequence", "kind", "result", "expression")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        definitions = {
            "sequence": ("#", 55, "center"),
            "kind": ("Instruction", 150, "w"),
            "result": ("Result / Target", 180, "w"),
            "expression": ("Expression / Operand", 470, "w"),
        }
        for name, (caption, width, anchor) in definitions.items():
            self.tree.heading(name, text=caption)
            self.tree.column(
                name,
                width=width,
                anchor=anchor,
                stretch=name == "expression",
            )
        vertical = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("label", foreground=COLORS.accent)
        self.tree.tag_configure("jump", foreground=COLORS.warning)
        self.tree.tag_configure("print", foreground=COLORS.violet)
        self.tree.tag_configure("operation", foreground=COLORS.text_soft)

    def set_content(self, content: str, _tag: str | None = None) -> None:
        self._raw_text = content
        self.instructions = parse_tac(content)
        self.tree.delete(*self.tree.get_children())
        for instruction in self.instructions:
            tag = self._tag_for(instruction.kind)
            self.tree.insert(
                "",
                "end",
                values=(
                    instruction.sequence,
                    instruction.kind,
                    instruction.result,
                    instruction.expression,
                ),
                tags=(tag,),
            )
        self.summary.set(
            f"{len(self.instructions)} TAC instruction"
            f"{'s' if len(self.instructions) != 1 else ''}"
        )
        self.notice.set(
            "Structured three-address code with labels and control flow"
            if self.instructions
            else self._empty_notice("No TAC instructions were found")
        )

    def clear(self) -> None:
        self._raw_text = ""
        self.instructions = ()
        self.tree.delete(*self.tree.get_children())
        self.summary.set("No TAC output")
        self.notice.set("")

    def focus_view(self) -> None:
        self.tree.focus_set()

    @staticmethod
    def _tag_for(kind: str) -> str:
        if kind == "Label":
            return "label"
        if "jump" in kind.casefold():
            return "jump"
        if kind == "Print":
            return "print"
        return "operation"

    def _empty_notice(self, fallback: str) -> str:
        first = self._raw_text.strip().splitlines()
        return first[0] if first else fallback
