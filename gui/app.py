"""Professional Tkinter IDE shell for the MiniLang compiler."""

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
from .diagnostics import Diagnostic, DiagnosticsView, parse_diagnostics
from .examples import DEFAULT_EXAMPLE, EXAMPLES
from .output_views import (
    ASTTreeView,
    StructuredOutputView,
    SymbolTableView,
    TACTableView,
    TokenTableView,
)
from .polish import ActivityIndicator, ToolTip, create_toolbar_icons
from .settings import AppSettings, SettingsStore
from .test_catalog import TestCase, TestCatalog
from .test_dashboard import TestDashboard
from .test_runner import RegressionSuiteRunner, SuiteSummary, TestResult
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
    "tokens": ("lexer",),
    "ast": ("parser", "ast"),
    "symtab": ("symtab", "semantic"),
    "tac": ("tac",),
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
        self.toolbar_icons = create_toolbar_icons(self)
        self.catalog = TestCatalog(self.project_root)
        self.settings_store = SettingsStore()
        self.saved_settings = self.settings_store.load()

        self.current_file: Path | None = None
        self.source_label = "Untitled.mc"
        self.current_test: TestCase | None = None
        self.is_dirty = False
        self.is_busy = False
        self._loading_content = False
        self._work_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._tree_cases: dict[str, TestCase] = {}
        self._action_buttons: list[ttk.Button] = []
        self._tooltips: list[ToolTip] = []
        self._test_cancel_event: threading.Event | None = None
        self.explorer_visible = tk.BooleanVar(value=True)
        self.output_visible = tk.BooleanVar(value=True)
        self.fullscreen_enabled = tk.BooleanVar(value=False)

        self.title(APP_NAME)
        self.geometry(self.saved_settings.geometry)
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
        self.after_idle(self._restore_layout)
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
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Find...",
            accelerator="Ctrl+F",
            command=lambda: self.editor.show_find_replace(False),
        )
        edit_menu.add_command(
            label="Replace...",
            accelerator="Ctrl+H",
            command=lambda: self.editor.show_find_replace(True),
        )
        edit_menu.add_command(
            label="Go to Line...",
            accelerator="Ctrl+G",
            command=self.editor_goto_safe,
        )
        edit_menu.add_separator()
        edit_menu.add_command(label="Zoom In", accelerator="Ctrl++", command=self.editor_zoom_in_safe)
        edit_menu.add_command(label="Zoom Out", accelerator="Ctrl+-", command=self.editor_zoom_out_safe)
        edit_menu.add_command(label="Reset Zoom", accelerator="Ctrl+0", command=self.editor_zoom_reset_safe)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        build_menu = tk.Menu(menu_bar)
        build_menu.add_command(label="Build Compiler", accelerator="Ctrl+B", command=self._build_compiler)
        build_menu.add_command(label="Run Full Pipeline", accelerator="F5", command=self._run_pipeline)
        build_menu.add_command(
            label="Run Regression Suite",
            accelerator="Ctrl+T",
            command=self._run_test_suite,
        )
        build_menu.add_separator()
        build_menu.add_command(label="Lexical Analysis", accelerator="Ctrl+1", command=lambda: self._run_mode("tokens"))
        build_menu.add_command(label="Parser / AST", accelerator="Ctrl+2", command=lambda: self._run_mode("ast"))
        build_menu.add_command(label="Semantic / Symbols", accelerator="Ctrl+3", command=lambda: self._run_mode("symtab"))
        build_menu.add_command(label="Generate TAC", accelerator="Ctrl+4", command=lambda: self._run_mode("tac"))
        menu_bar.add_cascade(label="Build", menu=build_menu)

        view_menu = tk.Menu(menu_bar)
        view_menu.add_command(label="Focus Explorer", command=self._focus_explorer)
        view_menu.add_command(label="Focus Editor", command=self.editor_focus_safe)
        view_menu.add_command(label="Focus Output", command=self._focus_output)
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Show Explorer",
            accelerator="Ctrl+Shift+E",
            variable=self.explorer_visible,
            command=self._toggle_explorer,
        )
        view_menu.add_checkbutton(
            label="Show Output Panel",
            accelerator="Ctrl+J",
            variable=self.output_visible,
            command=self._toggle_output_panel,
        )
        view_menu.add_checkbutton(
            label="Full Screen",
            accelerator="F11",
            variable=self.fullscreen_enabled,
            command=self._toggle_fullscreen,
        )
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
        # ttk.Label(
        #     title_area,
        #     text="Flex + Bison front-end  /  instructor-defined MiniLang specification",
        #     style="Subtitle.TLabel",
        # ).pack(anchor="w")

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
            ("New", "new", self._new_file, "New editor buffer (Ctrl+N)"),
            ("Open", "open", self._open_file, "Open source file (Ctrl+O)"),
            ("Save", "save", self._save_file, "Save current source (Ctrl+S)"),
        )
        for text, icon, command, tooltip in actions:
            button = ttk.Button(
                toolbar,
                text=text,
                image=self.toolbar_icons[icon],
                compound="left",
                command=command,
                style="Toolbar.TButton",
            )
            button.pack(side="left", padx=(0, 6))
            self._tooltips.append(ToolTip(button, tooltip, self.fonts))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=(4, 10))

        build_button = ttk.Button(
            toolbar,
            text="Build Compiler",
            image=self.toolbar_icons["build"],
            compound="left",
            command=self._build_compiler,
            style="Toolbar.TButton",
        )
        build_button.pack(side="left", padx=(0, 6))
        self._tooltips.append(
            ToolTip(build_button, "Build build/mcc using the project Makefile (Ctrl+B)", self.fonts)
        )
        run_button = ttk.Button(
            toolbar,
            text="Compile  F5",
            image=self.toolbar_icons["run"],
            compound="left",
            command=self._run_pipeline,
            style="Accent.TButton",
        )
        run_button.pack(side="left", padx=(0, 6))
        self._tooltips.append(
            ToolTip(run_button, "Run the complete compiler pipeline (F5)", self.fonts)
        )
        clear_button = ttk.Button(
            toolbar,
            text="Clear Outputs",
            image=self.toolbar_icons["clear"],
            compound="left",
            command=self._clear_outputs,
            style="Toolbar.TButton",
        )
        clear_button.pack(side="left", padx=(0, 6))
        self._tooltips.append(ToolTip(clear_button, "Clear compiler output panels", self.fonts))
        tests_button = ttk.Button(
            toolbar,
            text="Run 42 Tests",
            image=self.toolbar_icons["tests"],
            compound="left",
            command=self._run_test_suite,
            style="Toolbar.TButton",
        )
        tests_button.pack(side="left", padx=(0, 6))
        self._tooltips.append(
            ToolTip(tests_button, "Run the complete regression suite (Ctrl+T)", self.fonts)
        )
        load_button = ttk.Button(
            toolbar,
            text="Load Test",
            image=self.toolbar_icons["load"],
            compound="left",
            command=self._load_selected_test,
            style="Toolbar.TButton",
        )
        load_button.pack(side="left")
        self._tooltips.append(
            ToolTip(load_button, "Load the selected test as a protected copy", self.fonts)
        )
        self._action_buttons.extend((build_button, run_button, tests_button, load_button))

        self.activity_indicator = ActivityIndicator(toolbar)
        self.activity_indicator.pack(side="right", padx=(4, 8))
        ttk.Label(
            toolbar,
            text="F5 Compile  •  Ctrl+T Test Suite",
            style="Muted.TLabel",
        ).pack(side="right", padx=(8, 0))

    def _build_pipeline(self, parent: ttk.Frame) -> None:
        pipeline_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(8, 7))
        pipeline_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.pipeline = PipelineStrip(pipeline_frame, self.fonts)
        self.pipeline.pack(fill="x")
        phase_modes = {
            "lexer": "tokens",
            "parser": "ast",
            "ast": "ast",
            "symtab": "symtab",
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

        self.explorer_panel = self._build_test_explorer(self.main_pane)
        self.workspace_pane = ttk.Panedwindow(self.main_pane, orient="vertical")
        self.editor_panel = self._build_editor_panel(self.workspace_pane)
        self.output_panel = self._build_output_panel(self.workspace_pane)

        self.main_pane.add(self.explorer_panel, weight=0)
        self.main_pane.add(self.workspace_pane, weight=1)
        self.workspace_pane.add(self.editor_panel, weight=3)
        self.workspace_pane.add(self.output_panel, weight=2)

    def _build_test_explorer(self, parent: tk.Misc) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Surface.TFrame", padding=8, width=310)
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

        self.editor = CodeEditor(
            panel, on_change=self._editor_changed, fonts=self.fonts
        )
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
        self.output_views: dict[str, OutputView | StructuredOutputView] = {}

        compiler_view = OutputView(self.output_notebook, self.fonts)
        self.output_notebook.add(compiler_view, text="Compiler Output")
        self.output_views["compiler"] = compiler_view

        token_view = TokenTableView(
            self.output_notebook, self.fonts, on_navigate=self._navigate_to_location
        )
        self.output_notebook.add(token_view, text="Lexical Output")
        self.output_views["tokens"] = token_view

        ast_view = ASTTreeView(
            self.output_notebook, self.fonts, on_navigate=self._navigate_to_location
        )
        self.output_notebook.add(ast_view, text="Syntax / AST")
        self.output_views["ast"] = ast_view

        symbol_view = SymbolTableView(
            self.output_notebook, self.fonts, on_navigate=self._navigate_to_location
        )
        self.output_notebook.add(symbol_view, text="Semantic / Symbols")
        self.output_views["symtab"] = symbol_view

        tac_view = TACTableView(self.output_notebook, self.fonts)
        self.output_notebook.add(tac_view, text="Three Address Code")
        self.output_views["tac"] = tac_view

        self.diagnostics_view = DiagnosticsView(
            self.output_notebook,
            self.fonts,
            on_activate=self._activate_diagnostic,
        )
        self.output_notebook.add(self.diagnostics_view, text="Errors")

        warnings_view = OutputView(self.output_notebook, self.fonts)
        self.output_notebook.add(warnings_view, text="Warnings")
        self.output_views["warnings"] = warnings_view

        console_view = OutputView(self.output_notebook, self.fonts)
        self.output_notebook.add(console_view, text="Console")
        self.output_views["console"] = console_view

        build_view = OutputView(self.output_notebook, self.fonts)
        self.output_notebook.add(build_view, text="Build Log")
        self.output_views["build"] = build_view

        self.test_dashboard = TestDashboard(
            self.output_notebook,
            self.fonts,
            on_run=self._run_test_suite,
            on_cancel=self._cancel_test_suite,
            on_open_source=self._open_test_result,
        )
        self.output_notebook.add(self.test_dashboard, text="Test Suite")

        expected_view = OutputView(self.output_notebook, self.fonts)
        self.output_notebook.add(expected_view, text="Expected Output")
        self.output_views["expected"] = expected_view
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

    def _open_test_result(self, result: TestResult) -> None:
        result_path = result.source_path.resolve()
        for case in self.catalog.cases:
            if case.source_path.resolve() == result_path:
                self._load_test_case(case)
                return
        if not self._confirm_discard_changes():
            return
        try:
            content = result.source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror(
                "Load failed", f"Could not read {result.source_path}:\n\n{exc}"
            )
            return
        self.current_test = None
        self._set_editor_content(
            content,
            file_path=None,
            source_label=f"Test: {result.name}",
            dirty=False,
        )
        self.path_heading.set(f"Read-only copy from {result.name}")
        self.compiler_status.set(f"Loaded {result.name}")

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
        self._open_project_path(Path(selected), confirm=False)

    def _open_project_path(self, path: Path, confirm: bool = True) -> None:
        if confirm and not self._confirm_discard_changes():
            return
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
        if hasattr(self, "diagnostics_view"):
            self.diagnostics_view.clear("No diagnostics for this source")
        self.editor.focus_editor()

    def _editor_changed(self) -> None:
        if not self._loading_content:
            self._set_dirty(True)
            if hasattr(self, "diagnostics_view"):
                self.diagnostics_view.clear("Source changed - run the compiler again")
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
        self._log_console("Compiler build started: make")
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

    def _run_test_suite(self) -> None:
        if self.is_busy:
            self.compiler_status.set("Another operation is already running")
            return
        if not self._refresh_compiler_state():
            messagebox.showerror(
                "Compiler unavailable",
                "Build the project first, then run the regression suite.\n\n"
                f"Expected compiler:\n{self.runner.compiler_path}",
            )
            return

        suite_runner = RegressionSuiteRunner(
            self.project_root, self.runner.compiler_path
        )
        total = len(suite_runner.specs)
        if not total:
            messagebox.showwarning(
                "No tests found", "The project regression sources could not be discovered."
            )
            return
        if not self._begin_work(f"Running {total} regression checks..."):
            return

        self._test_cancel_event = threading.Event()
        self.pipeline.reset()
        self.test_dashboard.begin(total)
        self.output_notebook.select(self.test_dashboard)
        self._log_console(f"Regression suite started ({total} checks).")
        threading.Thread(
            target=self._test_suite_worker,
            args=(suite_runner, self._test_cancel_event),
            name="minilang-regression-suite",
            daemon=True,
        ).start()

    def _test_suite_worker(
        self,
        suite_runner: RegressionSuiteRunner,
        cancel_event: threading.Event,
    ) -> None:
        try:
            summary = suite_runner.run(
                progress=lambda result, index, total: self._work_queue.put(
                    ("test_progress", (result, index, total))
                ),
                cancel_event=cancel_event,
            )
            self._work_queue.put(("test_complete", summary))
        except Exception as exc:
            self._work_queue.put(("worker_error", f"Test suite worker failed: {exc}"))

    def _cancel_test_suite(self) -> None:
        if self._test_cancel_event is None or not self.is_busy:
            return
        self._test_cancel_event.set()
        self.test_dashboard.cancel_pending()
        self.compiler_status.set("Cancelling regression suite...")
        self._log_console("Regression suite cancellation requested.", "warning")

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
        self._log_console(
            "Compiler pipeline started: "
            + ", ".join(MODE_LABELS[mode] for mode in modes)
        )
        self.output_views["compiler"].set_content(
            "Compiler pipeline is running...\n", "warning"
        )
        self.output_views["warnings"].set_content(
            "Scanning compiler output for warnings...\n"
        )
        for mode in modes:
            for phase in MODE_PHASES[mode]:
                self.pipeline.set_state(phase, "running")
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
                elif event == "test_progress":
                    result, index, total = payload  # type: ignore[misc]
                    self.test_dashboard.add_result(result, index, total)
                elif event == "test_complete":
                    self._show_test_summary(payload)  # type: ignore[arg-type]
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
        self._log_console(
            f"Compiler build {'passed' if result.ok else 'failed'} "
            f"(exit {result.return_code}, {result.duration_ms} ms).",
            "success" if result.ok else "error",
        )
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
            for phase in MODE_PHASES[mode]:
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
        diagnostic_sources = list(unique_errors)
        for result in results.values():
            if not result.ok and " Error [line " in result.stdout:
                diagnostic_sources.append(result.stdout.strip())
        parsed_diagnostics = tuple(
            dict.fromkeys(parse_diagnostics("\n\n".join(diagnostic_sources)))
        )
        if diagnostic_sources:
            diagnostics.extend(("", "COMPILER DIAGNOSTICS", "===================="))
            if unique_errors:
                diagnostics.extend(unique_errors)
            else:
                for item in parsed_diagnostics:
                    diagnostics.append(
                        f"{item.phase} {item.severity} [line {item.line}, "
                        f"col {item.column}]: {item.message}"
                    )
                    if item.hint:
                        diagnostics.append(f"  --> hint: {item.hint}")
        else:
            diagnostics.extend(("", "No compiler errors or warnings were reported."))
        diagnostic_report = "\n".join(diagnostics) + "\n"
        self.diagnostics_view.set_diagnostics(
            parsed_diagnostics,
            diagnostic_report,
        )
        self.editor.set_diagnostics(parsed_diagnostics)

        token_count = self._extract_token_count(results)
        error_count = len(parsed_diagnostics) or self._extract_error_count(results)
        warning_lines = self._extract_warnings(results)
        warning_count = len(warning_lines)
        compiler_report = [
            "MINILANG COMPILER PIPELINE",
            "==========================",
            f"Source: {self.source_label}",
            "",
            *status_lines,
            "",
            f"Result: {'SUCCESS' if all_successful else 'FAILED'}",
            f"Total time: {total_duration} ms",
            f"Tokens: {token_count}",
            f"Errors: {error_count}",
            f"Warnings: {warning_count}",
        ]
        self.output_views["compiler"].set_content(
            "\n".join(compiler_report) + "\n",
            "success" if all_successful else "error",
        )
        if warning_lines:
            self.output_views["warnings"].set_content(
                "COMPILER WARNINGS\n=================\n\n"
                + "\n".join(warning_lines)
                + "\n",
                "warning",
            )
        else:
            self.output_views["warnings"].set_content(
                "No compiler warnings were reported.\n", "success"
            )
        self.metrics_status.set(
            f"Tokens {token_count}  |  Errors {error_count}  |  Warnings {warning_count}"
        )
        self.run_status.set(f"Exit {max_exit}  |  Time {total_duration} ms")
        if all_successful:
            self.compiler_status.set(f"Pipeline completed successfully in {total_duration} ms")
            if "tac" in results:
                self.output_notebook.select(self.output_views["tac"])
        else:
            self.compiler_status.set(f"Pipeline finished with {error_count or 1} error(s)")
            self.output_notebook.select(self.diagnostics_view)
        self._log_console(
            f"Compiler pipeline {'passed' if all_successful else 'failed'} "
            f"(exit {max_exit}, {total_duration} ms).",
            "success" if all_successful else "error",
        )
        self._end_work()

    def _show_test_summary(self, summary: SuiteSummary) -> None:
        self.test_dashboard.finish(summary)
        self._test_cancel_event = None
        if summary.cancelled:
            self.compiler_status.set(
                f"Regression suite cancelled after {summary.total} check(s)"
            )
            self.run_status.set(f"Cancelled  |  Time {summary.duration_ms} ms")
            level = "warning"
            message = (
                f"Regression suite cancelled: {summary.passed} passed, "
                f"{summary.failed} failed, {summary.total} completed "
                f"in {summary.duration_ms} ms."
            )
        else:
            self.compiler_status.set(
                "All regression checks passed"
                if summary.ok
                else f"Regression suite failed {summary.failed} check(s)"
            )
            self.run_status.set(
                f"Exit {0 if summary.ok else 1}  |  Time {summary.duration_ms} ms"
            )
            level = "success" if summary.ok else "error"
            message = (
                f"Regression suite complete: {summary.passed}/{summary.total} passed, "
                f"{summary.failed} failed in {summary.duration_ms} ms."
            )
        self.metrics_status.set(
            f"Tests {summary.total}  |  Passed {summary.passed}  |  Failed {summary.failed}"
        )
        self._log_console(message, level)
        self._end_work()

    def _show_worker_error(self, message: str) -> None:
        self.diagnostics_view.set_message(message)
        self.editor.clear_diagnostics()
        self.output_notebook.select(self.diagnostics_view)
        self.compiler_status.set("Internal GUI worker error")
        self._test_cancel_event = None
        if hasattr(self, "test_dashboard"):
            self.test_dashboard.run_button.configure(state="normal")
            self.test_dashboard.stop_button.configure(state="disabled")
        self._log_console(message, "error")
        self._end_work()

    def _begin_work(self, status: str) -> bool:
        if self.is_busy:
            return False
        self.is_busy = True
        for button in self._action_buttons:
            button.configure(state="disabled")
        self.activity_indicator.start()
        self.compiler_status.set(status)
        return True

    def _end_work(self) -> None:
        self.is_busy = False
        for button in self._action_buttons:
            button.configure(state="normal")
        self.activity_indicator.stop()

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

    @staticmethod
    def _extract_warnings(results: dict[str, CompilerResult]) -> tuple[str, ...]:
        warnings: list[str] = []
        seen: set[str] = set()
        for result in results.values():
            for line in f"{result.stdout}\n{result.stderr}".splitlines():
                cleaned = line.strip()
                if not cleaned or re.search(r"\bwarning\b", cleaned, re.IGNORECASE) is None:
                    continue
                if cleaned not in seen:
                    seen.add(cleaned)
                    warnings.append(cleaned)
        return tuple(warnings)

    # ------------------------------------------------------------------
    # General UI helpers
    # ------------------------------------------------------------------
    def _clear_outputs(self) -> None:
        messages = {
            "compiler": "Run the compiler to view the complete pipeline summary.\n",
            "tac": "Run TAC generation to view intermediate code.\n",
            "build": "Run Build Compiler to capture the Makefile output.\n",
            "tokens": "Run Lexical Analysis to view the token stream.\n",
            "ast": "Run Parser / AST to view the abstract syntax tree.\n",
            "symtab": "Run Semantic / Symbols to view the symbol table.\n",
            "warnings": "No compiler warnings.\n",
            "console": "Session console ready.\n",
        }
        for key, message in messages.items():
            self.output_views[key].set_content(message)
        self.diagnostics_view.clear("No diagnostics")
        self.editor.clear_diagnostics()
        if self.current_test is not None:
            self._show_expected_output(self.current_test)
        else:
            self.output_views["expected"].clear()
        self.pipeline.reset()
        self.metrics_status.set("Tokens 0  |  Errors 0  |  Warnings 0")
        self.run_status.set("Exit --  |  Time --")
        self.compiler_status.set("Outputs cleared")

    def _log_console(self, message: str, tag: str | None = None) -> None:
        view = self.output_views.get("console")
        if isinstance(view, OutputView):
            view.append(f"[{time.strftime('%H:%M:%S')}] {message}\n", tag)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _event: self._new_file())
        self.bind("<Control-o>", lambda _event: self._open_file())
        self.bind("<Control-s>", lambda _event: self._save_file())
        self.bind("<Control-Shift-S>", lambda _event: self._save_file_as())
        self.bind("<Control-b>", lambda _event: self._build_compiler())
        self.bind("<Control-t>", lambda _event: self._run_test_suite())
        self.bind("<Control-Shift-e>", self._keyboard_toggle_explorer)
        self.bind("<Control-j>", self._keyboard_toggle_output)
        self.bind("<F5>", lambda _event: self._run_pipeline())
        self.bind("<F11>", self._keyboard_toggle_fullscreen)
        self.bind("<Escape>", self._leave_fullscreen)
        self.bind("<Control-Key-1>", lambda _event: self._run_mode("tokens"))
        self.bind("<Control-Key-2>", lambda _event: self._run_mode("ast"))
        self.bind("<Control-Key-3>", lambda _event: self._run_mode("symtab"))
        self.bind("<Control-Key-4>", lambda _event: self._run_mode("tac"))
        self.bind("<Control-a>", lambda _event: self._select_all())
        self.bind("<Control-f>", lambda _event: self.editor.show_find_replace(False))
        self.bind("<Control-h>", lambda _event: self.editor.show_find_replace(True))
        self.bind("<Control-g>", lambda _event: self.editor.show_goto_line())
        self.bind_all("<KeyRelease>", self._update_cursor_status, add="+")
        self.bind_all("<ButtonRelease-1>", self._update_cursor_status, add="+")

    def _update_cursor_status(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if not hasattr(self, "editor"):
            return
        line, column = self.editor.cursor_position()
        self.cursor_status.set(f"Ln {line}, Col {column}")

    def _set_initial_splitters(self) -> None:
        self.explorer_visible.set(True)
        self.output_visible.set(True)
        self._toggle_explorer()
        self._toggle_output_panel()
        try:
            self.main_pane.sashpos(0, 285)
            available = max(self.workspace_pane.winfo_height(), 700)
            self.workspace_pane.sashpos(0, int(available * 0.62))
        except tk.TclError:
            pass

    def _restore_layout(self) -> None:
        try:
            self.main_pane.sashpos(0, self.saved_settings.main_sash)
            self.workspace_pane.sashpos(0, self.saved_settings.workspace_sash)
            tabs = self.output_notebook.tabs()
            if tabs:
                selected = min(self.saved_settings.selected_tab, len(tabs) - 1)
                self.output_notebook.select(tabs[selected])
        except tk.TclError:
            self._set_initial_splitters()

    def _save_layout(self) -> None:
        try:
            main_sash = (
                self.main_pane.sashpos(0)
                if str(self.explorer_panel) in self.main_pane.panes()
                else self.saved_settings.main_sash
            )
            workspace_sash = (
                self.workspace_pane.sashpos(0)
                if str(self.output_panel) in self.workspace_pane.panes()
                else self.saved_settings.workspace_sash
            )
            settings = AppSettings(
                geometry=self.geometry(),
                main_sash=main_sash,
                workspace_sash=workspace_sash,
                selected_tab=self.output_notebook.index("current"),
            )
            self.settings_store.save(settings)
        except (OSError, tk.TclError):
            pass

    def _focus_explorer(self) -> None:
        if not self.explorer_visible.get():
            self.explorer_visible.set(True)
            self._toggle_explorer()
        self.test_tree.focus_set()

    def _toggle_explorer(self) -> None:
        present = str(self.explorer_panel) in self.main_pane.panes()
        if self.explorer_visible.get() and not present:
            self.main_pane.insert(0, self.explorer_panel, weight=0)
            self.after_idle(lambda: self.main_pane.sashpos(0, 285))
        elif not self.explorer_visible.get() and present:
            self.main_pane.forget(self.explorer_panel)

    def _toggle_output_panel(self) -> None:
        present = str(self.output_panel) in self.workspace_pane.panes()
        if self.output_visible.get() and not present:
            self.workspace_pane.add(self.output_panel, weight=2)
            self.after_idle(self._restore_output_splitter)
        elif not self.output_visible.get() and present:
            self.workspace_pane.forget(self.output_panel)

    def _restore_output_splitter(self) -> None:
        try:
            available = max(self.workspace_pane.winfo_height(), 700)
            self.workspace_pane.sashpos(0, int(available * 0.62))
        except tk.TclError:
            pass

    def _toggle_fullscreen(self) -> None:
        self.attributes("-fullscreen", self.fullscreen_enabled.get())

    def _keyboard_toggle_explorer(self, _event: tk.Event[tk.Misc]) -> str:
        self.explorer_visible.set(not self.explorer_visible.get())
        self._toggle_explorer()
        return "break"

    def _keyboard_toggle_output(self, _event: tk.Event[tk.Misc]) -> str:
        self.output_visible.set(not self.output_visible.get())
        self._toggle_output_panel()
        return "break"

    def _keyboard_toggle_fullscreen(self, _event: tk.Event[tk.Misc]) -> str:
        self.fullscreen_enabled.set(not self.fullscreen_enabled.get())
        self._toggle_fullscreen()
        return "break"

    def _leave_fullscreen(self, _event: tk.Event[tk.Misc]) -> None:
        if self.fullscreen_enabled.get():
            self.fullscreen_enabled.set(False)
            self._toggle_fullscreen()

    def editor_focus_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.focus_editor()

    def editor_goto_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.show_goto_line()

    def editor_zoom_in_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.zoom_in()

    def editor_zoom_out_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.zoom_out()

    def editor_zoom_reset_safe(self) -> None:
        if hasattr(self, "editor"):
            self.editor.reset_zoom()

    def _activate_diagnostic(self, diagnostic: Diagnostic) -> None:
        self.editor.goto_diagnostic(diagnostic)
        self.compiler_status.set(
            f"{diagnostic.phase} error at line {diagnostic.line}, "
            f"column {diagnostic.column}"
        )

    def _navigate_to_location(self, line: int, column: int) -> None:
        self.editor.goto_location(line, column)
        self.compiler_status.set(f"Navigated to line {line}, column {column}")

    def _focus_output(self) -> None:
        if not self.output_visible.get():
            self.output_visible.set(True)
            self._toggle_output_panel()
        current = self.output_notebook.select()
        if current:
            widget = self.nametowidget(current)
            if isinstance(widget, OutputView):
                widget.text.focus_set()
            elif isinstance(widget, DiagnosticsView):
                widget.focus_view()
            elif isinstance(widget, StructuredOutputView):
                widget.focus_view()
            elif isinstance(widget, TestDashboard):
                widget.focus_view()

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
            "Operation running", "A background operation is still running. Close anyway?"
        ):
            return
        if self._confirm_discard_changes():
            if self._test_cancel_event is not None:
                self._test_cancel_event.set()
            self._save_layout()
            self.destroy()


def launch(project_root: Path | str, compiler_path: Path | str | None = None) -> None:
    """Construct the existing GUI entry point with the upgraded application shell."""
    runner = CompilerRunner(project_root=project_root, compiler_path=compiler_path)
    app = MiniLangIDE(runner)
    app.mainloop()
