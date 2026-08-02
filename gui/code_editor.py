from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class LineNumberCanvas(tk.Canvas):
    def __init__(self, parent: tk.Misc, text_widget: tk.Text, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget

    def redraw(self) -> None:
        self.delete("all")
        index = self.text_widget.index("@0,0")
        while True:
            line_info = self.text_widget.dlineinfo(index)
            if line_info is None:
                break
            y_position = line_info[1]
            line_number = index.split(".")[0]
            self.create_text(
                46,
                y_position,
                anchor="ne",
                text=line_number,
                fill="#64748b",
                font=("Cascadia Code", 10),
            )
            index = self.text_widget.index(f"{index}+1line")


class CodeEditor(ttk.Frame):
    KEYWORDS = ("int", "float", "bool", "if", "else", "while", "print")
    LITERALS = ("true", "false")
    TOKEN_PATTERN = re.compile(
        r"(?P<block_comment>/\*.*?\*/)"
        r"|(?P<line_comment>//[^\n]*)"
        r"|(?P<number>\b(?:\d+\.\d+|\d+)\b)"
        r"|(?P<keyword>\b(?:int|float|bool|if|else|while|print)\b)"
        r"|(?P<literal>\b(?:true|false)\b)"
        r"|(?P<operator><=|>=|==|!=|&&|\|\||[+\-*/%<>=!])",
        re.DOTALL,
    )

    def __init__(self, parent: tk.Misc, on_change: Callable[[], None] | None = None) -> None:
        super().__init__(parent, style="Editor.TFrame")
        self._on_change = on_change
        self._highlight_job: str | None = None

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self,
            wrap="none",
            undo=True,
            maxundo=-1,
            autoseparators=True,
            background="#0b1220",
            foreground="#dbeafe",
            insertbackground="#67e8f9",
            selectbackground="#164e63",
            selectforeground="#ecfeff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            font=("Cascadia Code", 11),
            tabs=("2c",),
        )
        self.line_numbers = LineNumberCanvas(
            self,
            self.text,
            width=56,
            background="#080e1a",
            highlightthickness=0,
        )
        self.vertical_scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self._scroll_vertical
        )
        self.horizontal_scrollbar = ttk.Scrollbar(
            self, orient="horizontal", command=self.text.xview
        )
        self.text.configure(
            yscrollcommand=self._on_vertical_scroll,
            xscrollcommand=self.horizontal_scrollbar.set,
        )

        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=2, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=1, sticky="ew")

        self._configure_tags()
        self.text.bind("<<Modified>>", self._text_modified)
        self.text.bind("<Configure>", self._redraw)
        self.text.bind("<KeyRelease>", self._cursor_moved, add="+")
        self.text.bind("<ButtonRelease-1>", self._cursor_moved, add="+")
        self.text.bind("<Tab>", self._insert_spaces)
        self.text.bind("<Return>", self._auto_indent)

    def _configure_tags(self) -> None:
        self.text.tag_configure("keyword", foreground="#67e8f9")
        self.text.tag_configure("literal", foreground="#c4b5fd")
        self.text.tag_configure("number", foreground="#fbbf24")
        self.text.tag_configure("operator", foreground="#f472b6")
        self.text.tag_configure("line_comment", foreground="#64748b")
        self.text.tag_configure("block_comment", foreground="#64748b")
        self.text.tag_configure("current_line", background="#0f1b2d")
        self.text.tag_lower("current_line")

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_text(self, content: str, *, reset_undo: bool = True) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        if reset_undo:
            self.text.edit_reset()
        self.text.edit_modified(False)
        self._highlight_now()
        self._mark_current_line()
        self.line_numbers.redraw()

    def cursor_position(self) -> tuple[int, int]:
        line, column = self.text.index("insert").split(".")
        return int(line), int(column) + 1

    def focus_editor(self) -> None:
        self.text.focus_set()

    def _text_modified(self, _event: tk.Event[tk.Misc]) -> None:
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self._schedule_highlight()
        self.line_numbers.redraw()
        if self._on_change is not None:
            self._on_change()

    def _schedule_highlight(self) -> None:
        if self._highlight_job is not None:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(120, self._highlight_now)

    def _highlight_now(self) -> None:
        self._highlight_job = None
        for tag_name in (
            "keyword",
            "literal",
            "number",
            "operator",
            "line_comment",
            "block_comment",
        ):
            self.text.tag_remove(tag_name, "1.0", "end")

        content = self.get_text()
        for match in self.TOKEN_PATTERN.finditer(content):
            tag_name = match.lastgroup
            if tag_name is None:
                continue
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add(tag_name, start, end)

    def _mark_current_line(self) -> None:
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")

    def _cursor_moved(self, _event: tk.Event[tk.Misc]) -> None:
        self._mark_current_line()
        self.line_numbers.redraw()

    def _redraw(self, _event: tk.Event[tk.Misc]) -> None:
        self.line_numbers.redraw()

    def _scroll_vertical(self, *args: str) -> None:
        self.text.yview(*args)
        self.line_numbers.redraw()

    def _on_vertical_scroll(self, first: str, last: str) -> None:
        self.vertical_scrollbar.set(first, last)
        self.line_numbers.redraw()

    def _insert_spaces(self, _event: tk.Event[tk.Misc]) -> str:
        self.text.insert("insert", "    ")
        return "break"

    def _auto_indent(self, _event: tk.Event[tk.Misc]) -> str:
        line_start = self.text.get("insert linestart", "insert")
        indentation = re.match(r"[ \t]*", line_start).group(0)
        if line_start.rstrip().endswith("{"):
            indentation += "    "
        self.text.insert("insert", "\n" + indentation)
        return "break"
