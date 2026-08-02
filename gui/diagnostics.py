from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .theme import COLORS, ThemeFonts


DIAGNOSTIC_PATTERN = re.compile(
    r"^(Lexical|Syntax|Semantic) Error \[line (\d+), col (\d+)\]:\s*(.+)$"
)
HINT_PATTERN = re.compile(r"^\s*-->\s*hint:\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Diagnostic:
    phase: str
    severity: str
    line: int
    column: int
    message: str
    hint: str = ""

    @property
    def location(self) -> str:
        return f"{self.line}:{self.column}"

    @property
    def full_message(self) -> str:
        if self.hint:
            return f"{self.message}\nSuggestion: {self.hint}"
        return self.message


def parse_diagnostics(text: str) -> tuple[Diagnostic, ...]:
    """Parse the compiler's stable line/column diagnostic format."""
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = DIAGNOSTIC_PATTERN.match(lines[index])
        if match is None:
            index += 1
            continue

        phase, line, column, message = match.groups()
        hint = ""
        if index + 1 < len(lines):
            hint_match = HINT_PATTERN.match(lines[index + 1])
            if hint_match is not None:
                hint = hint_match.group(1).strip()
                index += 1
        diagnostics.append(
            Diagnostic(
                phase=phase,
                severity="Error",
                line=int(line),
                column=int(column),
                message=message.strip(),
                hint=hint,
            )
        )
        index += 1
    return tuple(diagnostics)


class DiagnosticsView(ttk.Frame):
    """Structured table that can navigate directly to editor locations."""

    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        on_activate: Callable[[Diagnostic], None],
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=6)
        self.fonts = fonts
        self.on_activate = on_activate
        self._diagnostics: dict[str, Diagnostic] = {}
        self._raw_text = ""

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        actions = ttk.Frame(self, style="Surface.TFrame")
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        actions.columnconfigure(3, weight=1)
        ttk.Button(
            actions, text="Copy All", command=self.copy_all, style="Toolbar.TButton"
        ).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(
            actions, text="Save As...", command=self.save_as, style="Toolbar.TButton"
        ).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(
            actions, text="Clear", command=self.clear, style="Toolbar.TButton"
        ).grid(row=0, column=2)
        self.summary = tk.StringVar(value="No diagnostics")
        ttk.Label(actions, textvariable=self.summary, style="Muted.TLabel").grid(
            row=0, column=3, sticky="e", padx=(10, 4)
        )

        table_frame = ttk.Frame(self, style="Surface.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("severity", "phase", "line", "column", "message")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "severity": ("Severity", 85, "center"),
            "phase": ("Phase", 95, "center"),
            "line": ("Line", 55, "center"),
            "column": ("Col", 55, "center"),
            "message": ("Message", 520, "w"),
        }
        for name, (caption, width, anchor) in headings.items():
            self.tree.heading(name, text=caption)
            self.tree.column(
                name,
                width=width,
                minwidth=45,
                anchor=anchor,
                stretch=name == "message",
            )
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("error", foreground=COLORS.danger)
        self.tree.tag_configure("warning", foreground=COLORS.warning)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", self._activate_selected)
        self.tree.bind("<Return>", self._activate_selected)

        self.detail = tk.Text(
            self,
            height=3,
            wrap="word",
            state="disabled",
            background=COLORS.background_deep,
            foreground=COLORS.text_soft,
            selectbackground=COLORS.selection,
            relief="flat",
            padx=10,
            pady=7,
            font=(fonts.ui, 9),
        )
        self.detail.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def set_diagnostics(
        self,
        diagnostics: Iterable[Diagnostic],
        raw_text: str,
    ) -> None:
        self._clear_table()
        diagnostic_list = tuple(diagnostics)
        self._raw_text = raw_text
        for diagnostic in diagnostic_list:
            item = self.tree.insert(
                "",
                "end",
                values=(
                    diagnostic.severity,
                    diagnostic.phase,
                    diagnostic.line,
                    diagnostic.column,
                    diagnostic.message,
                ),
                tags=(diagnostic.severity.casefold(),),
            )
            self._diagnostics[item] = diagnostic
        count = len(diagnostic_list)
        self.summary.set(f"{count} error{'s' if count != 1 else ''}")
        if diagnostic_list:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
            self.tree.see(first)
        else:
            self._set_detail("No compiler errors or warnings were reported.")

    def set_message(self, message: str) -> None:
        self._clear_table()
        self._raw_text = message
        self.summary.set("Compiler message")
        self._set_detail(message)

    def clear(self, message: str = "No diagnostics") -> None:
        self._clear_table()
        self._raw_text = ""
        self.summary.set(message)
        self._set_detail("Select a compiler diagnostic to inspect its details.")

    def get_content(self) -> str:
        return self._raw_text

    def copy_all(self) -> None:
        if not self._raw_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self._raw_text)

    def save_as(self) -> None:
        if not self._raw_text:
            messagebox.showinfo("Nothing to save", "There are no diagnostics to save.")
            return
        selected = filedialog.asksaveasfilename(
            title="Save diagnostics",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            Path(selected).write_text(self._raw_text, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save diagnostics:\n\n{exc}")

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _selection_changed(self, _event: tk.Event[tk.Misc]) -> None:
        diagnostic = self._selected_diagnostic()
        if diagnostic is not None:
            self._set_detail(
                f"{diagnostic.phase} {diagnostic.severity} at "
                f"line {diagnostic.line}, column {diagnostic.column}\n"
                f"{diagnostic.full_message}"
            )

    def _activate_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        diagnostic = self._selected_diagnostic()
        if diagnostic is not None:
            self.on_activate(diagnostic)

    def _selected_diagnostic(self) -> Diagnostic | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._diagnostics.get(selection[0])

    def _clear_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._diagnostics.clear()

    def _set_detail(self, content: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", content)
        self.detail.configure(state="disabled")
