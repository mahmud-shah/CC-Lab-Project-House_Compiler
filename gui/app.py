from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .code_editor import CodeEditor
from .compiler_runner import CompilerResult, CompilerRunner
from .examples import DEFAULT_EXAMPLE, EXAMPLES
from .test_catalog import TestCase, TestCatalog
from .theme import COLORS, ThemeFonts, apply_theme
from .widgets import OutputView, PipelineStrip


APP_NAME = "MiniLang Compiler Studio"
MODE_ORDER = ("tokens", "ast", "symtab", "tac")
MODE_LABELS = {
    "tokens": "Lexical Analysis",
    "ast": "Parser / AST",
    "symtab": "Semantic / Symbol Table",
    "tac": "Three Address Code",
}
MODE_PHASES = {
    "tokens": "lexer",
    "ast": "parser",
    "symtab": "semantic",
    "tac": "tac",
}
MODE_TABS = {
    "tokens": "tokens",
    "ast": "ast",
    "symtab": "symtab",
    "tac": "tac",
}


@dataclass(frozen=True)
class BuildResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.return_code == 0


class MiniLangIDE(tk.Tk):
    """Modern, test-aware desktop shell around the existing mcc executable."""

    def __init__(self, runner: CompilerRunner) -> None:
        super().__init__()
        self.runner = runner
        self.project_root = runner.project_root
        self.fonts: ThemeFonts = apply_theme(self)
        self.catalog = TestCatalog(self.project_root)

        self.current_file: Path | None = None
        self.source_label = "Untitled.mc"
        self.current_test: TestCase | None = None
        self.is_dirty = False
        self.is_busy = False
        self._loading_content = False
        self._work_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._tree_cases: dict[str, TestCase] = {}
        self._action_buttons: list[ttk.Button] = []

        self.title(APP_NAME)
        self.geometry("1560x920")
        self.minsize(1120, 700)
        self.configure(background=COLORS.background)
        self.protocol("WM_DELETE_WINDOW", self._close_requested)

        self._build_menu()
        self._build_interface()
        self._bind_shortcuts()
        self._populate_test_tree()
        self._load_initial_source()
        self._refresh_compiler_state()
        self._clear_outputs()
        self.after(80, self._poll_work_queue)
        self.after_idle(self._set_initial_splitters)
        self.after_idle(self.editor.focus_editor)

    # ------------------------------------------------------------------
    # Interface construction
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self._new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self._open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_file)
        file_menu.add_command(
            label="Save As...", accelerator="Ctrl+Shift+S", command=self._save_file_as
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._close_requested)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self._undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self._redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self._editor_event("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self._editor_event("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self._editor_event("<<Paste>>"))
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self._select_all)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        build_menu = tk.Menu(menu_bar)
        build_menu.add_command(label="Build Compiler", accelerator="Ctrl+B", command=self._build_compiler)
        build_menu.add_command(label="Run Full Pipeline", accelerator="F5", command=self._run_pipeline)
        build_menu.add_separator()
        build_menu.add_command(label="Lexical Analysis", accelerator="Ctrl+1", command=lambda: self._run_mode("tokens"))
        build_menu.add_command(label="Parser / AST", accelerator="Ctrl+2", command=lambda: self._run_mode("ast"))
        build_menu.add_command(label="Semantic / Symbols", accelerator="Ctrl+3", command=lambda: self._run_mode("symtab"))
        build_menu.add_command(label="Generate TAC", accelerator="Ctrl+4", command=lambda: self._run_mode("tac"))
        menu_bar.add_cascade(label="Build", menu=build_menu)

        view_menu = tk.Menu(menu_bar)
        view_menu.add_command(label="Focus Test Explorer", command=self._focus_explorer)
        view_menu.add_command(label="Focus Editor", command=self.editor_focus_safe)
        view_menu.add_command(label="Focus Output", command=self._focus_output)
        view_menu.add_separator()
        view_menu.add_command(label="Reset Panel Layout", command=self._set_initial_splitters)
        menu_bar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menu_bar)
        help_menu.add_command(label="About MiniLang Studio", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self.configure(menu=menu_bar)

    def _build_interface(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=(12, 10, 12, 7))
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        self._build_header(root)
        self._build_toolbar(root)
        self._build_pipeline(root)
        self._build_workspace(root)
        self._build_statusbar(root)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        header.columnconfigure(0, weight=1)

        title_area = ttk.Frame(header, style="App.TFrame")
        title_area.grid(row=0, column=0, sticky="w")
        ttk.Label(title_area, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_area,
            text="Flex + Bison front-end  /  instructor-defined MiniLang specification",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        metrics = ttk.Frame(header, style="App.TFrame")
        metrics.grid(row=0, column=1, sticky="e")
        self.compiler_badge = tk.Label(
            metrics,
            text="CHECKING COMPILER",
            background=COLORS.warning_dark,
            foreground=COLORS.warning,
            font=(self.fonts.ui, 8, "bold"),
            padx=12,
            pady=7,
            cursor="hand2",
        )
        self.compiler_badge.pack(side="right")

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Toolbar.TFrame", padding=7)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        actions = (
            ("New", self._new_file, "Toolbar.TButton"),
            ("Open", self._open_file, "Toolbar.TButton"),
            ("Save", self._save_file, "Toolbar.TButton"),
        )
        for text, command, style in actions:
            button = ttk.Button(toolbar, text=text, command=command, style=style)
            button.pack(side="left", padx=(0, 6))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=(4, 10))

        build_button = ttk.Button(
            toolbar,
            text="Build Compiler",
            command=self._build_compiler,
            style="Toolbar.TButton",
        )
        build_button.pack(side="left", padx=(0, 6))
        run_button = ttk.Button(
            toolbar,
            text="Compile / Generate TAC   F5",
            command=self._run_pipeline,
            style="Accent.TButton",
        )
        run_button.pack(side="left", padx=(0, 6))
        clear_button = ttk.Button(
            toolbar,
            text="Clear Outputs",
            command=self._clear_outputs,
            style="Toolbar.TButton",
        )
        clear_button.pack(side="left", padx=(0, 6))
        load_button = ttk.Button(
            toolbar,
            text="Load Selected Test",
            command=self._load_selected_test,
            style="Toolbar.TButton",
        )
        load_button.pack(side="left")
        self._action_buttons.extend((build_button, run_button, load_button))

        ttk.Label(
            toolbar,
            text="Double-click a test to load it without modifying the original",
            style="Muted.TLabel",
        ).pack(side="right", padx=8)

    def _build_pipeline(self, parent: ttk.Frame) -> None:
        pipeline_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(8, 7))
        pipeline_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.pipeline = PipelineStrip(pipeline_frame, self.fonts)
        self.pipeline.pack(fill="x")
        phase_modes = {
            "lexer": "tokens",
            "parser": "ast",
            "semantic": "symtab",
            "tac": "tac",
        }
        for phase, mode in phase_modes.items():
            self.pipeline.bind_phase(
                phase, lambda _event, selected=mode: self._run_mode(selected)
            )

    def _build_workspace(self, parent: ttk.Frame) -> None:
        self.main_pane = ttk.Panedwindow(parent, orient="horizontal")
        self.main_pane.grid(row=3, column=0, sticky="nsew")

        explorer = self._build_test_explorer(self.main_pane)
        self.workspace_pane = ttk.Panedwindow(self.main_pane, orient="vertical")
        editor_panel = self._build_editor_panel(self.workspace_pane)
        output_panel = self._build_output_panel(self.workspace_pane)

        self.main_pane.add(explorer, weight=0)
        self.main_pane.add(self.workspace_pane, weight=1)
        self.workspace_pane.add(editor_panel, weight=3)
        self.workspace_pane.add(output_panel, weight=2)

    def _build_test_explorer(self, parent: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Surface.TFrame", padding=8, width=290)
        frame.pack_propagate(False)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        heading = ttk.Frame(frame, style="Surface.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="TEST EXPLORER", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(heading, text="REAL PROJECT TESTS", style="Muted.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        self.test_filter = tk.StringVar()
        search = ttk.Entry(frame, textvariable=self.test_filter)
        search.grid(row=1, column=0, sticky="ew", pady=(0, 7))
        self.test_filter.trace_add("write", lambda *_args: self._populate_test_tree())

        tree_frame = ttk.Frame(frame, style="Surface.TFrame")
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.test_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.test_tree.yview
        )
        self.test_tree.configure(yscrollcommand=tree_scroll.set)
        self.test_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.test_tree.tag_configure("example", foreground=COLORS.accent)
        self.test_tree.tag_configure("valid", foreground=COLORS.success)
        self.test_tree.tag_configure("invalid", foreground=COLORS.danger)
        self.test_tree.tag_configure("group", foreground=COLORS.text)
        self.test_tree.bind("<Double-1>", lambda _event: self._load_selected_test())
        self.test_tree.bind("<Return>", lambda _event: self._load_selected_test())
        self.test_tree.bind("<<TreeviewSelect>>", self._test_selection_changed)

        self.catalog_summary = tk.StringVar(value=self.catalog.summary)
        ttk.Label(
            frame,
            textvariable=self.catalog_summary,
            style="Muted.TLabel",
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(7, 0))
        return frame

    def _build_editor_panel(self, parent: tk.Misc) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Surface.TFrame", padding=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        heading = ttk.Frame(panel, style="Surface.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        heading.columnconfigure(0, weight=1)
        self.file_heading = tk.StringVar(value="Untitled.mc")
        ttk.Label(
            heading, textvariable=self.file_heading, style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        self.path_heading = tk.StringVar(value="Unsaved editor buffer")
        ttk.Label(
            heading, textvariable=self.path_heading, style="Muted.TLabel"
        ).grid(row=0, column=1, sticky="e")

        self.editor = CodeEditor(panel, on_change=self._editor_changed)
        self.editor.grid(row=1, column=0, sticky="nsew")
        return panel

    def _build_output_panel(self, parent: tk.Misc) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Surface.TFrame", padding=8)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        heading = ttk.Frame(panel, style="Surface.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="COMPILER OUTPUT", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            heading,
            text="Outputs come directly from build/mcc",
            style="Muted.TLabel",
        ).grid(row=0, column=1, sticky="e")

        self.output_notebook = ttk.Notebook(panel)
        self.output_notebook.grid(row=1, column=0, sticky="nsew")
        definitions = (
            ("tac", "TAC Output", ".tac"),
            ("diagnostics", "Diagnostics", ".txt"),
            ("build", "Build Log", ".txt"),
            ("tokens", "Tokens", ".txt"),
            ("ast", "AST", ".txt"),
            ("symtab", "Symbol Table", ".txt"),
            ("expected", "Expected Output", ".txt"),
        )
        self.output_views: dict[str, OutputView] = {}
        self.output_tabs: dict[str, OutputView] = {}
        for key, caption, extension in definitions:
            view = OutputView(
                self.output_notebook, self.fonts, save_extension=extension
            )
            self.output_notebook.add(view, text=caption)
            self.output_views[key] = view
            self.output_tabs[key] = view
        return panel

    def _build_statusbar(self, parent: ttk.Frame) -> None:
        status = ttk.Frame(parent, style="App.TFrame")
        status.grid(row=4, column=0, sticky="ew", pady=(7, 0))
        status.columnconfigure(1, weight=1)

        self.file_status = tk.StringVar(value="Untitled.mc  |  saved")
        self.compiler_status = tk.StringVar(value="Ready")
        self.cursor_status = tk.StringVar(value="Ln 1, Col 1")
        self.metrics_status = tk.StringVar(value="Tokens 0  |  Errors 0  |  Warnings 0")
        self.run_status = tk.StringVar(value="Exit --  |  Time --")

        ttk.Label(status, textvariable=self.file_status, style="Status.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 14)
        )
        ttk.Label(status, textvariable=self.compiler_status, style="Status.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(status, textvariable=self.cursor_status, style="Status.TLabel").grid(
            row=0, column=2, sticky="e", padx=(14, 14)
        )
        ttk.Label(status, textvariable=self.metrics_status, style="Status.TLabel").grid(
            row=0, column=3, sticky="e", padx=(0, 14)
        )
        ttk.Label(status, textvariable=self.run_status, style="Status.TLabel").grid(
            row=0, column=4, sticky="e"
        )

    # ------------------------------------------------------------------
    # Test catalogue
    # ------------------------------------------------------------------
    def _populate_test_tree(self) -> None:
        if not hasattr(self, "test_tree"):
            return
        self.test_tree.delete(*self.test_tree.get_children())
        self._tree_cases.clear()
        group_nodes: dict[tuple[str, ...], str] = {}
        cases = self.catalog.filtered(self.test_filter.get())

        for case in cases:
            parent = ""
            for level in range(1, len(case.group) + 1):
                group_key = case.group[:level]
                if group_key not in group_nodes:
                    node = self.test_tree.insert(
                        parent,
                        "end",
                        text=group_key[-1],
                        open=level == 1,
                        tags=("group",),
                    )
                    group_nodes[group_key] = node
                parent = group_nodes[group_key]
            item = self.test_tree.insert(
                parent,
                "end",
                text=case.label,
                tags=(case.kind,),
            )
            self._tree_cases[item] = case

        self.catalog_summary.set(
            self.catalog.summary if not self.test_filter.get() else f"{len(cases)} matching source files"
        )

    def _selected_test(self) -> TestCase | None:
        selection = self.test_tree.selection()
        if not selection:
            return None
        return self._tree_cases.get(selection[0])

    def _test_selection_changed(self, _event: tk.Event[tk.Misc]) -> None:
        case = self._selected_test()
        if case is None:
            return
        expected = case.expected_path.name if case.expected_path else "none"
        self.compiler_status.set(
            f"Selected {case.relative_path}  |  expected output: {expected}"
        )

    def _load_selected_test(self) -> None:
        case = self._selected_test()
        if case is None:
            messagebox.showinfo(
                "Select a test",
                "Select a source file in the Test Explorer, then choose Load Selected Test.",
            )
            return
        self._load_test_case(case)

    def _load_test_case(self, case: TestCase, confirm: bool = True) -> None:
        if confirm and not self._confirm_discard_changes():
            return
        try:
            content = case.source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Load failed", f"Could not read {case.source_path}:\n\n{exc}")
            return

        self.current_test = case
        self._set_editor_content(
            content,
            file_path=None,
            source_label=f"Example: {case.relative_path}",
            dirty=False,
        )
        self.path_heading.set(f"Read-only copy from {case.relative_path}")
        self._show_expected_output(case)
        self.compiler_status.set(f"Loaded {case.relative_path}")

    def _show_expected_output(self, case: TestCase) -> None:
        if case.expected_path is None:
            self.output_views["expected"].set_content(
                "This source has no separate golden output file.\n"
            )
            return
        try:
            content = case.expected_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            content = f"Could not read expected output:\n{exc}\n"
        heading = case.expected_path.relative_to(self.project_root).as_posix()
        self.output_views["expected"].set_content(f"{heading}\n{'=' * len(heading)}\n\n{content}")

    # ------------------------------------------------------------------
    # File and editor actions
    # ------------------------------------------------------------------
    def _load_initial_source(self) -> None:
        example = next((case for case in self.catalog.cases if case.kind == "example"), None)
        if example is not None:
            self._load_test_case(example, confirm=False)
        else:
            self._set_editor_content(
                EXAMPLES[DEFAULT_EXAMPLE],
                file_path=None,
                source_label=f"Example: {DEFAULT_EXAMPLE}",
                dirty=False,
            )

    def _new_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.current_test = None
        self._set_editor_content("", file_path=None, source_label="Untitled.mc", dirty=False)
        self.path_heading.set("Unsaved editor buffer")
        self.output_views["expected"].clear()
        self.compiler_status.set("New source buffer")

    def _open_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        selected = filedialog.askopenfilename(
            title="Open MiniLang source",
            filetypes=(("MiniLang source", "*.mc"), ("All files", "*.*")),
        )
        if not selected:
            return
        path = Path(selected)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Open failed", f"Could not open {path}:\n\n{exc}")
            return
        self.current_test = None
        self._set_editor_content(
            content, file_path=path, source_label=path.name, dirty=False
        )
        self.path_heading.set(str(path))
        self.output_views["expected"].clear()
        self.compiler_status.set(f"Opened {path}")

    def _save_file(self) -> bool:
        if self.current_file is None:
            return self._save_file_as()
        return self._write_current_file()

    def _save_file_as(self) -> bool:
        selected = filedialog.asksaveasfilename(
            title="Save MiniLang source",
            defaultextension=".mc",
            filetypes=(("MiniLang source", "*.mc"), ("All files", "*.*")),
        )
        if not selected:
            return False
        self.current_file = Path(selected)
        self.current_test = None
        self.source_label = self.current_file.name
        return self._write_current_file()

    def _write_current_file(self) -> bool:
        assert self.current_file is not None
        try:
            self.current_file.write_text(self.editor.get_text(), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save {self.current_file}:\n\n{exc}")
            return False
        self.path_heading.set(str(self.current_file))
        self._set_dirty(False)
        self.compiler_status.set(f"Saved {self.current_file}")
        return True

    def _set_editor_content(
        self,
        content: str,
        *,
        file_path: Path | None,
        source_label: str,
        dirty: bool,
    ) -> None:
        self._loading_content = True
        try:
            self.editor.set_text(content)
        finally:
            self._loading_content = False
        self.current_file = file_path
        self.source_label = source_label
        self._set_dirty(dirty)
        self.pipeline.reset()
        self.editor.focus_editor()

    def _editor_changed(self) -> None:
        if not self._loading_content:
            self._set_dirty(True)
        self._update_cursor_status()

    def _set_dirty(self, value: bool) -> None:
        self.is_dirty = value
        marker = " *" if value else ""
        state = "modified" if value else "saved"
        self.file_heading.set(self.source_label + marker)
        self.file_status.set(f"{self.source_label}{marker}  |  {state}")
        self.title(f"{self.source_label}{marker} — {APP_NAME}")

    def _confirm_discard_changes(self) -> bool:
        if not self.is_dirty:
            return True
        choice = messagebox.askyesnocancel(
            "Unsaved changes", "Save changes before continuing?"
        )
        if choice is None:
            return False
        if choice:
            return self._save_file()
        return True

    def _editor_event(self, event_name: str) -> None:
        self.editor.text.event_generate(event_name)
        self.editor.focus_editor()

    def _undo(self) -> None:
        try:
            self.editor.text.edit_undo()
        except tk.TclError:
            pass

    def _redo(self) -> None:
        try:
            self.editor.text.edit_redo()
        except tk.TclError:
            pass

    def _select_all(self) -> str:
        self.editor.text.tag_add("sel", "1.0", "end-1c")
        self.editor.text.mark_set("insert", "1.0")
        self.editor.text.see("insert")
        return "break"

    # ------------------------------------------------------------------
    # Build and compiler execution
    # ------------------------------------------------------------------
    def _refresh_compiler_state(self) -> bool:
        ready, message = self.runner.validate()
        if ready:
            self.compiler_badge.configure(
                text="COMPILER READY",
                background=COLORS.success_dark,
                foreground=COLORS.success,
            )
        else:
            self.compiler_badge.configure(
                text="COMPILER UNAVAILABLE",
                background=COLORS.danger_dark,
                foreground=COLORS.danger,
            )
        self.compiler_badge.bind(
            "<Button-1>", lambda _event: messagebox.showinfo("Compiler", message)
        )
        return ready

    def _build_compiler(self) -> None:
        if not self._begin_work("Building compiler with make..."):
            return
        self.pipeline.reset()
        self.output_views["build"].set_content(
            f"Working directory: {self.project_root}\nCommand: make\n\n",
            "heading",
        )
        self.output_notebook.select(self.output_views["build"])
        threading.Thread(
            target=self._build_worker,
            name="minilang-build",
            daemon=True,
        ).start()

    def _build_worker(self) -> None:
        started = time.perf_counter()
        command = ("make",)
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            build = BuildResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
        except subprocess.TimeoutExpired as exc:
            build = BuildResult(
                command=command,
                return_code=124,
                stdout=self._decode_process_output(exc.stdout),
                stderr=self._decode_process_output(exc.stderr)
                + "\nBuild timed out after 180 seconds.",
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
        except OSError as exc:
            build = BuildResult(
                command=command,
                return_code=126,
                stdout="",
                stderr=f"Could not start make: {exc}",
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
        self._work_queue.put(("build", build))

    def _run_pipeline(self) -> None:
        self._start_compilation(MODE_ORDER)

    def _run_mode(self, mode: str) -> None:
        self._start_compilation((mode,))

    def _start_compilation(self, modes: tuple[str, ...]) -> None:
        if self.is_busy:
            self.compiler_status.set("Another build or compilation is already running")
            return
        if not self._refresh_compiler_state():
            messagebox.showerror(
                "Compiler unavailable",
                "Build the project first, then try again.\n\n"
                f"Expected compiler:\n{self.runner.compiler_path}",
            )
            return
        source = self.editor.get_text()
        if not source.strip():
            messagebox.showwarning("No source", "Enter or load MiniLang source first.")
            return
        if not self._begin_work(
            "Running " + ", ".join(MODE_LABELS[mode] for mode in modes) + "..."
        ):
            return

        self.pipeline.reset()
        for mode in modes:
            self.pipeline.set_state(MODE_PHASES[mode], "running")
            self.output_views[MODE_TABS[mode]].set_content("Running compiler...\n", "warning")
        threading.Thread(
            target=self._compile_worker,
            args=(source, modes),
            name="minilang-pipeline",
            daemon=True,
        ).start()

    def _compile_worker(self, source: str, modes: tuple[str, ...]) -> None:
        try:
            results = self.runner.run_pipeline(source, modes)
            self._work_queue.put(("compile", results))
        except Exception as exc:
            self._work_queue.put(("worker_error", f"Compiler worker failed: {exc}"))

    def _poll_work_queue(self) -> None:
        try:
            while True:
                event, payload = self._work_queue.get_nowait()
                if event == "build":
                    self._show_build_result(payload)  # type: ignore[arg-type]
                elif event == "compile":
                    self._show_compiler_results(payload)  # type: ignore[arg-type]
                elif event == "worker_error":
                    self._show_worker_error(str(payload))
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(80, self._poll_work_queue)

    def _show_build_result(self, result: BuildResult) -> None:
        content = [
            f"Command: {' '.join(result.command)}",
            f"Exit code: {result.return_code}",
            f"Duration: {result.duration_ms} ms",
            "",
        ]
        if result.stdout.strip():
            content.extend(("STANDARD OUTPUT", "---------------", result.stdout.rstrip(), ""))
        if result.stderr.strip():
            content.extend(("STANDARD ERROR", "--------------", result.stderr.rstrip(), ""))
        if not result.stdout.strip() and not result.stderr.strip():
            content.append("Build completed without console output.")
        self.output_views["build"].set_content(
            "\n".join(content), "success" if result.ok else "error"
        )
        self.run_status.set(f"Exit {result.return_code}  |  Time {result.duration_ms} ms")
        self.compiler_status.set(
            "Compiler build completed successfully" if result.ok else "Compiler build failed — see Build Log"
        )
        self._refresh_compiler_state()
        self._end_work()

    def _show_compiler_results(self, results: dict[str, CompilerResult]) -> None:
        total_duration = 0
        all_successful = True
        unique_errors: list[str] = []
        seen_errors: set[str] = set()
        status_lines: list[str] = []
        max_exit = 0

        for mode, result in results.items():
            total_duration += result.duration_ms
            max_exit = max(max_exit, result.return_code)
            all_successful = all_successful and result.ok
            phase = MODE_PHASES[mode]
            self.pipeline.set_state(phase, "success" if result.ok else "error")
            output = result.stdout.rstrip()
            if not output:
                output = (
                    "Compilation completed successfully with no text output."
                    if result.ok
                    else "This compiler phase failed. See Diagnostics."
                )
            self.output_views[MODE_TABS[mode]].set_content(
                output + "\n", "success" if result.ok else "error"
            )
            status_lines.append(
                f"{MODE_LABELS[mode]:28} "
                f"{'PASS' if result.ok else 'FAIL'}  "
                f"exit={result.return_code}  time={result.duration_ms} ms"
            )
            error_text = result.stderr.strip()
            if error_text and error_text not in seen_errors:
                seen_errors.add(error_text)
                unique_errors.append(error_text)

        diagnostics = ["PIPELINE SUMMARY", "================", *status_lines]
        if unique_errors:
            diagnostics.extend(("", "COMPILER DIAGNOSTICS", "====================", *unique_errors))
        else:
            diagnostics.extend(("", "No compiler errors or warnings were reported."))
        self.output_views["diagnostics"].set_content(
            "\n".join(diagnostics) + "\n",
            "success" if all_successful else "error",
        )

        token_count = self._extract_token_count(results)
        error_count = self._extract_error_count(results)
        self.metrics_status.set(
            f"Tokens {token_count}  |  Errors {error_count}  |  Warnings 0"
        )
        self.run_status.set(f"Exit {max_exit}  |  Time {total_duration} ms")
        if all_successful:
            self.compiler_status.set(f"Pipeline completed successfully in {total_duration} ms")
            if "tac" in results:
                self.output_notebook.select(self.output_views["tac"])
        else:
            self.compiler_status.set(f"Pipeline finished with {error_count or 1} error(s)")
            self.output_notebook.select(self.output_views["diagnostics"])
        self._end_work()

    def _show_worker_error(self, message: str) -> None:
        self.output_views["diagnostics"].set_content(message + "\n", "error")
        self.output_notebook.select(self.output_views["diagnostics"])
        self.compiler_status.set("Internal GUI worker error")
        self._end_work()

    def _begin_work(self, status: str) -> bool:
        if self.is_busy:
            return False
        self.is_busy = True
        for button in self._action_buttons:
            button.configure(state="disabled")
        self.compiler_status.set(status)
        return True

    def _end_work(self) -> None:
        self.is_busy = False
        for button in self._action_buttons:
            button.configure(state="normal")

    @staticmethod
    def _decode_process_output(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    @staticmethod
    def _extract_token_count(results: dict[str, CompilerResult]) -> int:
        token_result = results.get("tokens")
        if token_result is None:
            return 0
        match = re.search(r"(\d+)\s+token\(s\)", token_result.stdout)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _extract_error_count(results: dict[str, CompilerResult]) -> int:
        counts: list[int] = []
        for result in results.values():
            matches = re.findall(r"(\d+)\s+error\(s\) found", result.stderr)
            counts.extend(int(value) for value in matches)
            if result.return_code and not matches:
                category_lines = re.findall(
                    r"^(?:Lexical|Syntax|Semantic) Error", result.stderr, re.MULTILINE
                )
                if category_lines:
                    counts.append(len(category_lines))
        return max(counts, default=0)

    # ------------------------------------------------------------------
    # General UI helpers
    # ------------------------------------------------------------------
    def _clear_outputs(self) -> None:
        messages = {
            "tac": "Run TAC generation to view intermediate code.\n",
            "diagnostics": "Compiler diagnostics and phase summaries will appear here.\n",
            "build": "Run Build Compiler to capture the Makefile output.\n",
            "tokens": "Run Lexical Analysis to view the token stream.\n",
            "ast": "Run Parser / AST to view the abstract syntax tree.\n",
            "symtab": "Run Semantic / Symbols to view the symbol table.\n",
        }
        for key, message in messages.items():
            self.output_views[key].set_content(message)
        if self.current_test is not None:
            self._show_expected_output(self.current_test)
        else:
            self.output_views["expected"].clear()
        self.pipeline.reset()
        self.metrics_status.set("Tokens 0  |  Errors 0  |  Warnings 0")
        self.run_status.set("Exit --  |  Time --")
        self.compiler_status.set("Outputs cleared")

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _event: self._new_file())
        self.bind("<Control-o>", lambda _event: self._open_file())
        self.bind("<Control-s>", lambda _event: self._save_file())
        self.bind("<Control-Shift-S>", lambda _event: self._save_file_as())
        self.bind("<Control-b>", lambda _event: self._build_compiler())
        self.bind("<F5>", lambda _event: self._run_pipeline())
        self.bind("<Control-Key-1>", lambda _event: self._run_mode("tokens"))
        self.bind("<Control-Key-2>", lambda _event: self._run_mode("ast"))
        self.bind("<Control-Key-3>", lambda _event: self._run_mode("symtab"))
        self.bind("<Control-Key-4>", lambda _event: self._run_mode("tac"))
        self.bind("<Control-a>", lambda _event: self._select_all())
        self.bind_all("<KeyRelease>", self._update_cursor_status, add="+")
        self.bind_all("<ButtonRelease-1>", self._update_cursor_status, add="+")

    def _update_cursor_status(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if not hasattr(self, "editor"):
            return
        line, column = self.editor.cursor_position()
        self.cursor_status.set(f"Ln {line}, Col {column}")

    def _set_initial_splitters(self) -> None:
        try:
            self.main_pane.sashpos(0, 285)
            available = max(self.workspace_pane.winfo_height(), 700)
            self.workspace_pane.sashpos(0, int(available * 0.62))
        except tk.TclError:
            pass

    def _focus_explorer(self) -> None:
        self.test_tree.focus_set()

    def editor_focus_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.focus_editor()

    def _focus_output(self) -> None:
        current = self.output_notebook.select()
        if current:
            widget = self.nametowidget(current)
            if isinstance(widget, OutputView):
                widget.text.focus_set()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About MiniLang Compiler Studio",
            "MiniLang Compiler Studio\n\n"
            "A professional Tkinter interface for the instructor-defined "
            "Flex/Bison compiler pipeline.\n\n"
            f"Discovered test sources: {len(self.catalog.cases)}\n"
            f"Compiler: {self.runner.compiler_path}",
        )

    def _close_requested(self) -> None:
        if self.is_busy and not messagebox.askyesno(
            "Operation running", "A build or compilation is still running. Close anyway?"
        ):
            return
        if self._confirm_discard_changes():
            self.destroy()


def launch(project_root: Path | str, compiler_path: Path | str | None = None) -> None:
    """Construct the existing GUI entry point with the upgraded application shell."""
    runner = CompilerRunner(project_root=project_root, compiler_path=compiler_path)
    app = MiniLangIDE(runner)
    app.mainloop()
