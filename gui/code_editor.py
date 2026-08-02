from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable, Iterable
from tkinter import messagebox, simpledialog, ttk

from .diagnostics import Diagnostic
from .theme import COLORS, ThemeFonts


class LineNumberCanvas(tk.Canvas):
    def __init__(self, parent: tk.Misc, editor: "CodeEditor") -> None:
        super().__init__(
            parent,
            width=70,
            background=COLORS.editor_gutter,
            highlightthickness=0,
            borderwidth=0,
        )
        self.editor = editor
        self.bind("<Button-1>", self._clicked)
        self.bind("<Motion>", self._motion)
        self.bind("<Leave>", lambda _event: self.editor.hide_diagnostic_tooltip())

    def redraw(self) -> None:
        self.delete("all")
        text = self.editor.text
        index = text.index("@0,0")
        while True:
            line_info = text.dlineinfo(index)
            if line_info is None:
                break
            y_position = line_info[1]
            line_number = int(index.split(".")[0])
            diagnostics = self.editor.diagnostics_for_line(line_number)
            if diagnostics:
                color = (
                    COLORS.danger
                    if any(item.severity.casefold() == "error" for item in diagnostics)
                    else COLORS.warning
                )
                self.create_oval(
                    9,
                    y_position + 5,
                    17,
                    y_position + 13,
                    fill=color,
                    outline=color,
                )
                if len(diagnostics) > 1:
                    self.create_text(
                        23,
                        y_position + 1,
                        anchor="nw",
                        text=str(len(diagnostics)),
                        fill=color,
                        font=(self.editor.fonts.ui, 7, "bold"),
                    )
            self.create_text(
                63,
                y_position,
                anchor="ne",
                text=str(line_number),
                fill=COLORS.muted,
                font=(self.editor.fonts.mono, self.editor.font_size),
            )
            index = text.index(f"{index}+1line")

    def _line_at(self, y_position: int) -> int:
        return int(self.editor.text.index(f"@0,{y_position}").split(".")[0])

    def _clicked(self, event: tk.Event[tk.Misc]) -> None:
        line = self._line_at(event.y)
        diagnostics = self.editor.diagnostics_for_line(line)
        if diagnostics:
            self.editor.goto_diagnostic(diagnostics[0])

    def _motion(self, event: tk.Event[tk.Misc]) -> None:
        line = self._line_at(event.y)
        self.editor.schedule_diagnostic_tooltip(line, event.x_root + 12, event.y_root + 12)


class DiagnosticTooltip:
    def __init__(self, parent: tk.Misc, fonts: ThemeFonts) -> None:
        self.parent = parent
        self.fonts = fonts
        self.window: tk.Toplevel | None = None

    def show(self, x: int, y: int, message: str) -> None:
        self.hide()
        window = tk.Toplevel(self.parent)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        window.configure(background=COLORS.danger)
        label = tk.Label(
            window,
            text=message,
            justify="left",
            wraplength=440,
            background=COLORS.danger_dark,
            foreground=COLORS.text,
            font=(self.fonts.ui, 9),
            padx=10,
            pady=8,
        )
        label.pack(padx=1, pady=1)
        self.window = window

    def hide(self) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class FindReplaceDialog(tk.Toplevel):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor
        self.title("Find and Replace")
        self.configure(background=COLORS.surface)
        self.resizable(False, False)
        self.transient(editor.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.find_value = tk.StringVar()
        self.replace_value = tk.StringVar()
        self.match_case = tk.BooleanVar(value=False)
        self.whole_word = tk.BooleanVar(value=False)
        self.result_text = tk.StringVar(value="Enter text to search")

        body = ttk.Frame(self, style="Surface.TFrame", padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Find", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 7)
        )
        self.find_entry = ttk.Entry(body, textvariable=self.find_value, width=38)
        self.find_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 7))

        self.replace_label = ttk.Label(body, text="Replace", style="SectionTitle.TLabel")
        self.replace_label.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 7))
        self.replace_entry = ttk.Entry(body, textvariable=self.replace_value, width=38)
        self.replace_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 7))

        ttk.Checkbutton(body, text="Match case", variable=self.match_case).grid(
            row=2, column=1, sticky="w"
        )
        ttk.Checkbutton(body, text="Whole word", variable=self.whole_word).grid(
            row=2, column=2, sticky="w"
        )

        buttons = ttk.Frame(body, style="Surface.TFrame")
        buttons.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 6))
        ttk.Button(
            buttons, text="Previous", command=lambda: self._find(-1), style="Toolbar.TButton"
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            buttons, text="Next", command=lambda: self._find(1), style="Accent.TButton"
        ).pack(side="left", padx=(0, 5))
        self.replace_button = ttk.Button(
            buttons, text="Replace", command=self._replace, style="Toolbar.TButton"
        )
        self.replace_button.pack(side="left", padx=(0, 5))
        self.replace_all_button = ttk.Button(
            buttons, text="Replace All", command=self._replace_all, style="Toolbar.TButton"
        )
        self.replace_all_button.pack(side="left")

        ttk.Label(body, textvariable=self.result_text, style="Muted.TLabel").grid(
            row=4, column=0, columnspan=4, sticky="w"
        )

        self.find_value.trace_add("write", lambda *_args: self._refresh_matches())
        self.match_case.trace_add("write", lambda *_args: self._refresh_matches())
        self.whole_word.trace_add("write", lambda *_args: self._refresh_matches())
        self.find_entry.bind("<Return>", lambda _event: self._find(1))
        self.find_entry.bind("<Shift-Return>", lambda _event: self._find(-1))
        self.bind("<Escape>", lambda _event: self.close())

    def show_mode(self, replace: bool) -> None:
        state = "normal" if replace else "disabled"
        self.replace_entry.configure(state=state)
        self.replace_button.configure(state=state)
        self.replace_all_button.configure(state=state)
        self.title("Replace" if replace else "Find")
        try:
            selected = self.editor.text.get("sel.first", "sel.last")
        except tk.TclError:
            selected = ""
        if selected and "\n" not in selected:
            self.find_value.set(selected)
        self.deiconify()
        self.lift()
        self.find_entry.focus_set()
        self.find_entry.selection_range(0, "end")
        self._refresh_matches()

    def close(self) -> None:
        self.editor.clear_search_highlights()
        self.withdraw()
        self.editor.focus_editor()

    def _options(self) -> tuple[str, bool, bool]:
        return self.find_value.get(), self.match_case.get(), self.whole_word.get()

    def _refresh_matches(self) -> None:
        query, match_case, whole_word = self._options()
        count = self.editor.highlight_search(query, match_case, whole_word)
        self.result_text.set(
            f"{count} match{'es' if count != 1 else ''}" if query else "Enter text to search"
        )

    def _find(self, direction: int) -> None:
        query, match_case, whole_word = self._options()
        position, total = self.editor.find_step(query, match_case, whole_word, direction)
        self.result_text.set(
            f"Match {position} of {total}" if total else "No matches found"
        )

    def _replace(self) -> None:
        query, match_case, whole_word = self._options()
        replaced = self.editor.replace_current(
            query, self.replace_value.get(), match_case, whole_word
        )
        self._refresh_matches()
        if not replaced:
            self.result_text.set("No current match to replace")

    def _replace_all(self) -> None:
        query, match_case, whole_word = self._options()
        count = self.editor.replace_all(
            query, self.replace_value.get(), match_case, whole_word
        )
        self.result_text.set(f"Replaced {count} occurrence{'s' if count != 1 else ''}")


class CodeEditor(ttk.Frame):
    TOKEN_PATTERN = re.compile(
        r"(?P<block_comment>/\*.*?\*/)"
        r"|(?P<line_comment>//[^\n]*)"
        r"|(?P<number>\b(?:\d+\.\d+|\d+)\b)"
        r"|(?P<keyword>\b(?:int|float|bool|if|else|while|print)\b)"
        r"|(?P<literal>\b(?:true|false)\b)"
        r"|(?P<operator><=|>=|==|!=|&&|\|\||[+\-*/%<>=!])",
        re.DOTALL,
    )
    OPENING_BRACKETS = {"(": ")", "{": "}"}
    CLOSING_BRACKETS = {")": "(", "}": "{"}

    def __init__(
        self,
        parent: tk.Misc,
        on_change: Callable[[], None] | None = None,
        fonts: ThemeFonts | None = None,
    ) -> None:
        super().__init__(parent, style="Editor.TFrame")
        self.fonts = fonts or ThemeFonts(ui="TkDefaultFont", mono="TkFixedFont")
        self.font_size = 11
        self._on_change = on_change
        self._highlight_job: str | None = None
        self._tooltip_job: str | None = None
        self._tooltip_line: int | None = None
        self._diagnostics_by_line: dict[int, list[Diagnostic]] = {}
        self._find_dialog: FindReplaceDialog | None = None
        self._search_ranges: list[tuple[str, str]] = []
        self._search_position = -1
        self.tooltip = DiagnosticTooltip(self, self.fonts)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self,
            wrap="none",
            undo=True,
            maxundo=-1,
            autoseparators=True,
            background=COLORS.editor,
            foreground=COLORS.text,
            insertbackground=COLORS.accent,
            selectbackground=COLORS.selection,
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=15,
            pady=12,
            spacing1=1,
            spacing3=1,
            font=(self.fonts.mono, self.font_size),
            tabs=("2c",),
        )
        self.line_numbers = LineNumberCanvas(self, self)
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
        self._bind_events()

    def _configure_tags(self) -> None:
        self.text.tag_configure("keyword", foreground=COLORS.accent)
        self.text.tag_configure("literal", foreground=COLORS.violet)
        self.text.tag_configure("number", foreground=COLORS.warning)
        self.text.tag_configure("operator", foreground="#f472b6")
        self.text.tag_configure("line_comment", foreground=COLORS.muted)
        self.text.tag_configure("block_comment", foreground=COLORS.muted)
        self.text.tag_configure("current_line", background="#0d1c2f")
        self.text.tag_configure(
            "bracket_match", background=COLORS.accent_dark, foreground="#ffffff"
        )
        self.text.tag_configure(
            "bracket_unmatched", background=COLORS.danger_dark, foreground=COLORS.danger
        )
        self.text.tag_configure("diagnostic_line", background="#1c111d")
        self.text.tag_configure(
            "diagnostic_error", foreground=COLORS.danger, underline=True
        )
        self.text.tag_configure(
            "search_match", background="#554512", foreground="#ffffff"
        )
        self.text.tag_configure(
            "search_current", background=COLORS.accent_active, foreground="#ffffff"
        )
        self.text.tag_lower("current_line")
        self.text.tag_lower("diagnostic_line")
        self.text.tag_raise("diagnostic_error")
        self.text.tag_raise("search_current")

    def _bind_events(self) -> None:
        self.text.bind("<<Modified>>", self._text_modified)
        self.text.bind("<Configure>", self._redraw)
        self.text.bind("<KeyRelease>", self._cursor_moved, add="+")
        self.text.bind("<ButtonRelease-1>", self._cursor_moved, add="+")
        self.text.bind("<Motion>", self._text_motion, add="+")
        self.text.bind("<Leave>", lambda _event: self.hide_diagnostic_tooltip())
        self.text.bind("<Tab>", self._insert_spaces)
        self.text.bind("<Shift-Tab>", self._unindent)
        self.text.bind("<Return>", self._auto_indent)
        self.text.bind("<KeyPress-braceright>", self._insert_closing_brace)
        self.text.bind("<Control-f>", lambda _event: self.show_find_replace(False))
        self.text.bind("<Control-h>", lambda _event: self.show_find_replace(True))
        self.text.bind("<Control-g>", lambda _event: self.show_goto_line())
        self.text.bind("<Control-plus>", lambda _event: self.zoom_in())
        self.text.bind("<Control-equal>", lambda _event: self.zoom_in())
        self.text.bind("<Control-minus>", lambda _event: self.zoom_out())
        self.text.bind("<Control-Key-0>", lambda _event: self.reset_zoom())
        self.text.bind("<Control-slash>", self._toggle_comment)
        self.text.bind("<Control-MouseWheel>", self._mouse_zoom)
        self.text.bind("<Control-Button-4>", lambda _event: self.zoom_in())
        self.text.bind("<Control-Button-5>", lambda _event: self.zoom_out())

    # Public API preserved from the original editor.
    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_text(self, content: str, *, reset_undo: bool = True) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        if reset_undo:
            self.text.edit_reset()
        self.text.edit_modified(False)
        self.clear_search_highlights()
        self.clear_diagnostics()
        self._highlight_now()
        self._cursor_moved()
        self.line_numbers.redraw()

    def cursor_position(self) -> tuple[int, int]:
        line, column = self.text.index("insert").split(".")
        return int(line), int(column) + 1

    def focus_editor(self) -> None:
        self.text.focus_set()

    # Diagnostics and navigation.
    def set_diagnostics(self, diagnostics: Iterable[Diagnostic]) -> None:
        self.clear_diagnostics()
        for diagnostic in diagnostics:
            self._diagnostics_by_line.setdefault(diagnostic.line, []).append(diagnostic)
            line_start = f"{diagnostic.line}.0"
            line_end = f"{diagnostic.line}.end"
            self.text.tag_add("diagnostic_line", line_start, f"{line_end}+1c")
            start = f"{diagnostic.line}.{max(diagnostic.column - 1, 0)}"
            if self.text.compare(start, ">", line_end):
                start = line_end
            end = f"{start}+1c"
            if self.text.compare(start, "==", line_end) and self.text.compare(
                line_start, "<", line_end
            ):
                start = f"{line_end}-1c"
                end = line_end
            self.text.tag_add("diagnostic_error", start, end)
        self.line_numbers.redraw()

    def clear_diagnostics(self) -> None:
        self._diagnostics_by_line.clear()
        self.text.tag_remove("diagnostic_line", "1.0", "end")
        self.text.tag_remove("diagnostic_error", "1.0", "end")
        self.hide_diagnostic_tooltip()
        self.line_numbers.redraw()

    def diagnostics_for_line(self, line: int) -> tuple[Diagnostic, ...]:
        return tuple(self._diagnostics_by_line.get(line, ()))

    def goto_diagnostic(self, diagnostic: Diagnostic) -> None:
        self.goto_location(diagnostic.line, diagnostic.column)

    def goto_location(self, line: int, column: int = 1) -> None:
        last_line = int(self.text.index("end-1c").split(".")[0])
        safe_line = max(1, min(line, last_line))
        line_end_column = int(self.text.index(f"{safe_line}.end").split(".")[1])
        safe_column = max(0, min(column - 1, line_end_column))
        index = f"{safe_line}.{safe_column}"
        self.text.mark_set("insert", index)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", index, f"{index}+1c")
        self.text.see(index)
        self.focus_editor()
        self._cursor_moved()

    def show_goto_line(self) -> str:
        maximum = int(self.text.index("end-1c").split(".")[0])
        current, _column = self.cursor_position()
        selected = simpledialog.askinteger(
            "Go to Line",
            f"Line number (1-{maximum}):",
            parent=self,
            initialvalue=current,
            minvalue=1,
            maxvalue=maximum,
        )
        if selected is not None:
            self.goto_location(selected, 1)
        return "break"

    # Find and replace.
    def show_find_replace(self, replace: bool = False) -> str:
        if self._find_dialog is None or not self._find_dialog.winfo_exists():
            self._find_dialog = FindReplaceDialog(self)
        self._find_dialog.show_mode(replace)
        return "break"

    def highlight_search(self, query: str, match_case: bool, whole_word: bool) -> int:
        self.clear_search_highlights()
        if not query:
            return 0
        content = self.get_text()
        pattern = re.escape(query)
        if whole_word:
            pattern = rf"\b{pattern}\b"
        flags = 0 if match_case else re.IGNORECASE
        for match in re.finditer(pattern, content, flags):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self._search_ranges.append((start, end))
            self.text.tag_add("search_match", start, end)
        if self._search_ranges:
            self._search_position = 0
            self._select_search_result(0)
        return len(self._search_ranges)

    def find_step(
        self,
        query: str,
        match_case: bool,
        whole_word: bool,
        direction: int,
    ) -> tuple[int, int]:
        if not self._search_ranges:
            self.highlight_search(query, match_case, whole_word)
        total = len(self._search_ranges)
        if not total:
            return 0, 0
        if self._search_position < 0:
            self._search_position = 0
        else:
            self._search_position = (self._search_position + direction) % total
        self._select_search_result(self._search_position)
        return self._search_position + 1, total

    def replace_current(
        self,
        query: str,
        replacement: str,
        match_case: bool,
        whole_word: bool,
    ) -> bool:
        if not self._search_ranges:
            self.highlight_search(query, match_case, whole_word)
        if not self._search_ranges or self._search_position < 0:
            return False
        start, end = self._search_ranges[self._search_position]
        self.text.edit_separator()
        self.text.delete(start, end)
        self.text.insert(start, replacement)
        self.text.edit_separator()
        self.highlight_search(query, match_case, whole_word)
        return True

    def replace_all(
        self,
        query: str,
        replacement: str,
        match_case: bool,
        whole_word: bool,
    ) -> int:
        if not query:
            return 0
        pattern = re.escape(query)
        if whole_word:
            pattern = rf"\b{pattern}\b"
        flags = 0 if match_case else re.IGNORECASE
        updated, count = re.subn(
            pattern, lambda _match: replacement, self.get_text(), flags=flags
        )
        if count:
            self.text.edit_separator()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", updated)
            self.text.edit_separator()
            self._schedule_highlight()
        self.highlight_search(query, match_case, whole_word)
        return count

    def clear_search_highlights(self) -> None:
        self.text.tag_remove("search_match", "1.0", "end")
        self.text.tag_remove("search_current", "1.0", "end")
        self._search_ranges.clear()
        self._search_position = -1

    def _select_search_result(self, position: int) -> None:
        self.text.tag_remove("search_current", "1.0", "end")
        start, end = self._search_ranges[position]
        self.text.tag_add("search_current", start, end)
        self.text.mark_set("insert", start)
        self.text.see(start)

    # Zoom.
    def zoom_in(self) -> str:
        self._set_font_size(self.font_size + 1)
        return "break"

    def zoom_out(self) -> str:
        self._set_font_size(self.font_size - 1)
        return "break"

    def reset_zoom(self) -> str:
        self._set_font_size(11)
        return "break"

    def _set_font_size(self, size: int) -> None:
        self.font_size = max(8, min(size, 24))
        self.text.configure(font=(self.fonts.mono, self.font_size))
        self.line_numbers.redraw()

    def _mouse_zoom(self, event: tk.Event[tk.Misc]) -> str:
        if event.delta > 0:
            return self.zoom_in()
        return self.zoom_out()

    # Tooltip handling.
    def schedule_diagnostic_tooltip(self, line: int, x: int, y: int) -> None:
        diagnostics = self.diagnostics_for_line(line)
        if not diagnostics:
            self.hide_diagnostic_tooltip()
            return
        if self._tooltip_line == line and self.tooltip.window is not None:
            return
        self.hide_diagnostic_tooltip()
        self._tooltip_line = line
        message = "\n\n".join(
            f"{item.phase} {item.severity} ({item.location})\n{item.full_message}"
            for item in diagnostics
        )
        self._tooltip_job = self.after(350, lambda: self.tooltip.show(x, y, message))

    def hide_diagnostic_tooltip(self) -> None:
        if self._tooltip_job is not None:
            self.after_cancel(self._tooltip_job)
            self._tooltip_job = None
        self._tooltip_line = None
        self.tooltip.hide()

    def _text_motion(self, event: tk.Event[tk.Misc]) -> None:
        line = int(self.text.index(f"@{event.x},{event.y}").split(".")[0])
        self.schedule_diagnostic_tooltip(line, event.x_root + 12, event.y_root + 12)

    # Editing behavior.
    def _text_modified(self, _event: tk.Event[tk.Misc]) -> None:
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self._schedule_highlight()
        self.line_numbers.redraw()
        if self._diagnostics_by_line:
            self.clear_diagnostics()
        if self._on_change is not None:
            self._on_change()

    def _schedule_highlight(self) -> None:
        if self._highlight_job is not None:
            self.after_cancel(self._highlight_job)
        self._highlight_job = self.after(100, self._highlight_now)

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
            self.text.tag_add(
                tag_name,
                f"1.0+{match.start()}c",
                f"1.0+{match.end()}c",
            )

    def _cursor_moved(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._mark_current_line()
        self._highlight_matching_bracket()
        self.line_numbers.redraw()

    def _mark_current_line(self) -> None:
        self.text.tag_remove("current_line", "1.0", "end")
        self.text.tag_add("current_line", "insert linestart", "insert lineend+1c")

    def _highlight_matching_bracket(self) -> None:
        self.text.tag_remove("bracket_match", "1.0", "end")
        self.text.tag_remove("bracket_unmatched", "1.0", "end")
        content = self.get_text()
        if not content:
            return
        count = self.text.count("1.0", "insert", "chars")
        offset = int(count[0]) if count else 0
        candidate = None
        for position in (offset - 1, offset):
            if 0 <= position < len(content) and content[position] in "(){}":
                candidate = position
                break
        if candidate is None:
            return
        character = content[candidate]
        if character in self.OPENING_BRACKETS:
            target = self.OPENING_BRACKETS[character]
            direction = 1
        else:
            target = self.CLOSING_BRACKETS[character]
            direction = -1
        depth = 0
        position = candidate
        match_position = None
        while 0 <= position < len(content):
            current = content[position]
            if current == character:
                depth += 1
            elif current == target:
                depth -= 1
                if depth == 0:
                    match_position = position
                    break
            position += direction
        candidate_index = f"1.0+{candidate}c"
        if match_position is None:
            self.text.tag_add("bracket_unmatched", candidate_index, f"{candidate_index}+1c")
            return
        match_index = f"1.0+{match_position}c"
        self.text.tag_add("bracket_match", candidate_index, f"{candidate_index}+1c")
        self.text.tag_add("bracket_match", match_index, f"{match_index}+1c")

    def _insert_spaces(self, _event: tk.Event[tk.Misc]) -> str:
        if self.text.tag_ranges("sel"):
            start_line, end_line = self._selected_line_range()
            for line in range(start_line, end_line + 1):
                self.text.insert(f"{line}.0", "    ")
        else:
            self.text.insert("insert", "    ")
        return "break"

    def _unindent(self, _event: tk.Event[tk.Misc]) -> str:
        start_line, end_line = self._selected_line_range()
        for line in range(start_line, end_line + 1):
            prefix = self.text.get(f"{line}.0", f"{line}.4")
            remove = len(prefix) - len(prefix.lstrip(" "))
            if remove:
                self.text.delete(f"{line}.0", f"{line}.{remove}")
            elif self.text.get(f"{line}.0", f"{line}.1") == "\t":
                self.text.delete(f"{line}.0", f"{line}.1")
        return "break"

    def _auto_indent(self, _event: tk.Event[tk.Misc]) -> str:
        before_cursor = self.text.get("insert linestart", "insert")
        after_cursor = self.text.get("insert", "insert lineend")
        match = re.match(r"[ \t]*", before_cursor)
        indentation = match.group(0) if match else ""
        opens_block = before_cursor.rstrip().endswith("{")
        closes_block = after_cursor.lstrip().startswith("}")
        if opens_block and closes_block:
            self.text.insert("insert", "\n" + indentation + "    " + "\n" + indentation)
            self.text.mark_set("insert", "insert-1line lineend")
        else:
            if opens_block:
                indentation += "    "
            self.text.insert("insert", "\n" + indentation)
        return "break"

    def _insert_closing_brace(self, _event: tk.Event[tk.Misc]) -> str | None:
        before_cursor = self.text.get("insert linestart", "insert")
        if before_cursor.strip():
            return None
        if before_cursor.endswith("    "):
            self.text.delete("insert-4c", "insert")
        elif before_cursor.endswith("\t"):
            self.text.delete("insert-1c", "insert")
        self.text.insert("insert", "}")
        return "break"

    def _toggle_comment(self, _event: tk.Event[tk.Misc]) -> str:
        start_line, end_line = self._selected_line_range()
        lines = [self.text.get(f"{line}.0", f"{line}.end") for line in range(start_line, end_line + 1)]
        uncomment = all(not line.strip() or line.lstrip().startswith("//") for line in lines)
        for line_number, line_text in zip(range(start_line, end_line + 1), lines):
            if not line_text.strip():
                continue
            indentation = len(line_text) - len(line_text.lstrip(" "))
            index = f"{line_number}.{indentation}"
            if uncomment:
                if self.text.get(index, f"{index}+2c") == "//":
                    self.text.delete(index, f"{index}+2c")
                    if self.text.get(index, f"{index}+1c") == " ":
                        self.text.delete(index, f"{index}+1c")
            else:
                self.text.insert(index, "// ")
        return "break"

    def _selected_line_range(self) -> tuple[int, int]:
        try:
            start = int(self.text.index("sel.first").split(".")[0])
            end_index = self.text.index("sel.last")
            end_line, end_column = (int(value) for value in end_index.split("."))
            if end_column == 0 and end_line > start:
                end_line -= 1
            return start, end_line
        except tk.TclError:
            line = int(self.text.index("insert").split(".")[0])
            return line, line

    def _redraw(self, _event: tk.Event[tk.Misc]) -> None:
        self.line_numbers.redraw()

    def _scroll_vertical(self, *args: str) -> None:
        self.text.yview(*args)
        self.line_numbers.redraw()

    def _on_vertical_scroll(self, first: str, last: str) -> None:
        self.vertical_scrollbar.set(first, last)
        self.line_numbers.redraw()