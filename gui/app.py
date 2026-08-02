from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .code_editor import CodeEditor
from .compiler_runner import CompilerResult, CompilerRunner
from .examples import DEFAULT_EXAMPLE, EXAMPLES


APP_NAME = "MiniLang Compiler Studio"
MODE_LABELS = {
    "tokens": "Tokens",
    "ast": "Abstract Syntax Tree",
    "symtab": "Symbol Table",
    "tac": "Three Address Code",
}
MODE_ORDER = tuple(MODE_LABELS)


class MiniLangIDE(tk.Tk):
    """A focused editor and inspection interface around the mcc binary."""

    def __init__(self, runner: CompilerRunner) -> None:
        super().__init__()
        self.runner = runner
        self.current_file: Path | None = None
        self.is_dirty = False
        self.is_running = False
        self._loading_content = False
        self._result_queue: queue.Queue[dict[str, CompilerResult]] = queue.Queue()

        self.title(APP_NAME)
        self.geometry("1420x860")
        self.minsize(1000, 650)
        self.configure(background="#07101f")
        self.protocol("WM_DELETE_WINDOW", self._close_requested)

        self._configure_styles()
        self._build_interface()
        self._bind_shortcuts()
        self._load_example(DEFAULT_EXAMPLE, confirm=False)
        self._refresh_compiler_state()
        self.after_idle(self.editor.focus_editor)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#07101f")
        style.configure("Panel.TFrame", background="#0b1526")
        style.configure("Editor.TFrame", background="#0b1220")
        style.configure(
            "Header.TLabel",
            background="#07101f",
            foreground="#f8fafc",
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Subtle.TLabel",
            background="#07101f",
            foreground="#94a3b8",
            font=("Segoe UI", 9),
        )
        style.configure(
            "PanelTitle.TLabel",
            background="#0b1526",
            foreground="#e2e8f0",
            font=("Segoe UI Semibold", 10),
        )
        style.configure(
            "Status.TLabel",
            background="#07101f",
            foreground="#94a3b8",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Accent.TButton",
            background="#0891b2",
            foreground="#ecfeff",
            padding=(14, 8),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#06b6d4"), ("disabled", "#164e63")],
            foreground=[("disabled", "#94a3b8")],
        )
        style.configure(
            "Toolbar.TButton",
            background="#132238",
            foreground="#dbeafe",
            padding=(10, 7),
            font=("Segoe UI", 9),
        )
        style.map(
            "Toolbar.TButton",
            background=[("active", "#1e3a5f"), ("disabled", "#111827")],
            foreground=[("disabled", "#64748b")],
        )
        style.configure(
            "TNotebook",
            background="#0b1526",
            borderwidth=0,
            tabmargins=(0, 4, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background="#111d30",
            foreground="#94a3b8",
            padding=(12, 8),
            font=("Segoe UI", 9),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#164e63"), ("active", "#152b45")],
            foreground=[("selected", "#ecfeff"), ("active", "#e2e8f0")],
        )
        style.configure(
            "TCombobox",
            fieldbackground="#111d30",
            background="#111d30",
            foreground="#e2e8f0",
            arrowcolor="#67e8f9",
            padding=5,
        )

    def _build_interface(self) -> None:
        root_frame = ttk.Frame(self, style="App.TFrame", padding=(16, 12, 16, 8))
        root_frame.pack(fill="both", expand=True)
        root_frame.columnconfigure(0, weight=1)
        root_frame.rowconfigure(2, weight=1)

        self._build_header(root_frame)
        self._build_toolbar(root_frame)
        self._build_workspace(root_frame)
        self._build_statusbar(root_frame)

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        title_group = ttk.Frame(header, style="App.TFrame")
        title_group.grid(row=0, column=0, sticky="w")
        ttk.Label(title_group, text=APP_NAME, style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_group,
            text="Edit MiniLang source and inspect every compiler phase",
            style="Subtle.TLabel",
        ).pack(anchor="w")

        self.compiler_badge = tk.Label(
            header,
            text="Checking compiler...",
            background="#3f2d12",
            foreground="#fde68a",
            padx=12,
            pady=7,
            font=("Segoe UI Semibold", 9),
        )
        self.compiler_badge.grid(row=0, column=1, sticky="e")

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent, style="Panel.TFrame", padding=8)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        for text, command in (
            ("New", self._new_file),
            ("Open", self._open_file),
            ("Save", self._save_file),
            ("Save As", self._save_file_as),
        ):
            ttk.Button(
                toolbar, text=text, command=command, style="Toolbar.TButton"
            ).pack(side="left", padx=(0, 6))

        separator = ttk.Separator(toolbar, orient="vertical")
        separator.pack(side="left", fill="y", padx=(4, 10))

        ttk.Label(toolbar, text="Example", style="PanelTitle.TLabel").pack(
            side="left", padx=(0, 6)
        )
        self.example_name = tk.StringVar(value=DEFAULT_EXAMPLE)
        example_picker = ttk.Combobox(
            toolbar,
            textvariable=self.example_name,
            values=list(EXAMPLES),
            state="readonly",
            width=22,
        )
        example_picker.pack(side="left", padx=(0, 6))
        example_picker.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._load_example(self.example_name.get()),
        )

        ttk.Button(
            toolbar,
            text="Load",
            command=lambda: self._load_example(self.example_name.get()),
            style="Toolbar.TButton",
        ).pack(side="left")

        self.pipeline_button = ttk.Button(
            toolbar,
            text="Run Full Pipeline  F5",
            command=self._run_pipeline,
            style="Accent.TButton",
        )
        self.pipeline_button.pack(side="right")

    def _build_workspace(self, parent: ttk.Frame) -> None:
        paned = ttk.Panedwindow(parent, orient="horizontal")
        paned.grid(row=2, column=0, sticky="nsew")

        editor_panel = ttk.Frame(paned, style="Panel.TFrame", padding=(10, 8))
        editor_panel.columnconfigure(0, weight=1)
        editor_panel.rowconfigure(1, weight=1)
        self.file_label = ttk.Label(
            editor_panel, text="Untitled.mc", style="PanelTitle.TLabel"
        )
        self.file_label.grid(row=0, column=0, sticky="w", pady=(0, 7))
        self.editor = CodeEditor(editor_panel, on_change=self._editor_changed)
        self.editor.grid(row=1, column=0, sticky="nsew")

        results_panel = ttk.Frame(paned, style="Panel.TFrame", padding=(10, 8))
        results_panel.columnconfigure(0, weight=1)
        results_panel.rowconfigure(2, weight=1)

        ttk.Label(
            results_panel, text="Compiler pipeline", style="PanelTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 7))
        self._build_stage_bar(results_panel)
        self._build_result_notebook(results_panel)

        paned.add(editor_panel, weight=5)
        paned.add(results_panel, weight=6)

    def _build_stage_bar(self, parent: ttk.Frame) -> None:
        stage_bar = ttk.Frame(parent, style="Panel.TFrame")
        stage_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for column in range(len(MODE_ORDER)):
            stage_bar.columnconfigure(column, weight=1)

        self.stage_labels: dict[str, tk.Label] = {}
        for column, mode in enumerate(MODE_ORDER):
            label = tk.Label(
                stage_bar,
                text=MODE_LABELS[mode],
                background="#111d30",
                foreground="#94a3b8",
                padx=8,
                pady=6,
                font=("Segoe UI", 8),
            )
            label.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0, 5 if column < len(MODE_ORDER) - 1 else 0),
            )
            label.bind("<Button-1>", lambda _event, item=mode: self._run_mode(item))
            label.configure(cursor="hand2")
            self.stage_labels[mode] = label

    def _build_result_notebook(self, parent: ttk.Frame) -> None:
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=2, column=0, sticky="nsew")

        self.output_widgets: dict[str, tk.Text] = {}
        self.tab_frames: dict[str, ttk.Frame] = {}
        for mode in MODE_ORDER:
            frame, output = self._create_output_tab()
            self.notebook.add(frame, text=MODE_LABELS[mode])
            self.output_widgets[mode] = output
            self.tab_frames[mode] = frame

        diagnostics_frame, diagnostics = self._create_output_tab()
        self.notebook.add(diagnostics_frame, text="Diagnostics")
        self.output_widgets["diagnostics"] = diagnostics
        self.tab_frames["diagnostics"] = diagnostics_frame

    def _create_output_tab(self) -> tuple[ttk.Frame, tk.Text]:
        frame = ttk.Frame(self.notebook, style="Panel.TFrame", padding=6)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        output = tk.Text(
            frame,
            wrap="none",
            state="disabled",
            background="#080e1a",
            foreground="#cbd5e1",
            insertbackground="#67e8f9",
            selectbackground="#164e63",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            font=("Cascadia Code", 10),
        )
        vertical = ttk.Scrollbar(frame, orient="vertical", command=output.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=output.xview)
        output.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        output.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return frame, output

    def _build_statusbar(self, parent: ttk.Frame) -> None:
        statusbar = ttk.Frame(parent, style="App.TFrame")
        statusbar.grid(row=3, column=0, sticky="ew", pady=(7, 0))
        statusbar.columnconfigure(0, weight=1)

        self.status_text = tk.StringVar(value="Ready")
        self.cursor_text = tk.StringVar(value="Ln 1, Col 1")
        ttk.Label(statusbar, textvariable=self.status_text, style="Status.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(statusbar, textvariable=self.cursor_text, style="Status.TLabel").grid(
            row=0, column=1, sticky="e"
        )

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-n>", lambda _event: self._new_file())
        self.bind("<Control-o>", lambda _event: self._open_file())
        self.bind("<Control-s>", lambda _event: self._save_file())
        self.bind("<Control-Shift-S>", lambda _event: self._save_file_as())
        self.bind("<F5>", lambda _event: self._run_pipeline())
        self.bind("<Control-Key-1>", lambda _event: self._run_mode("tokens"))
        self.bind("<Control-Key-2>", lambda _event: self._run_mode("ast"))
        self.bind("<Control-Key-3>", lambda _event: self._run_mode("symtab"))
        self.bind("<Control-Key-4>", lambda _event: self._run_mode("tac"))
        self.bind_all("<KeyRelease>", self._update_cursor_status, add="+")
        self.bind_all("<ButtonRelease-1>", self._update_cursor_status, add="+")

    def _refresh_compiler_state(self) -> bool:
        ready, message = self.runner.validate()
        if ready:
            self.compiler_badge.configure(
                text="Compiler ready", background="#12372a", foreground="#86efac"
            )
        else:
            self.compiler_badge.configure(
                text="Compiler unavailable",
                background="#451a24",
                foreground="#fda4af",
            )
        self.compiler_badge.configure(cursor="hand2")
        self.compiler_badge.bind(
            "<Button-1>", lambda _event: messagebox.showinfo("Compiler", message)
        )
        self.status_text.set(message)
        return ready

    def _new_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        self._set_editor_content("", file_path=None, dirty=False)
        self.status_text.set("New source file")

    def _open_file(self) -> None:
        if not self._confirm_discard_changes():
            return
        selected = filedialog.askopenfilename(
            title="Open MiniLang source",
            filetypes=(
                ("MiniLang source", "*.mc"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return
        path = Path(selected)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("Open failed", f"Could not open {path}:\n\n{exc}")
            return
        self._set_editor_content(content, file_path=path, dirty=False)
        self.status_text.set(f"Opened {path}")

    def _save_file(self) -> bool:
        if self.current_file is None:
            return self._save_file_as()
        return self._write_current_file()

    def _save_file_as(self) -> bool:
        selected = filedialog.asksaveasfilename(
            title="Save MiniLang source",
            defaultextension=".mc",
            filetypes=(
                ("MiniLang source", "*.mc"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return False
        self.current_file = Path(selected)
        return self._write_current_file()

    def _write_current_file(self) -> bool:
        assert self.current_file is not None
        try:
            self.current_file.write_text(self.editor.get_text(), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Save failed", f"Could not save {self.current_file}:\n\n{exc}"
            )
            return False
        self._set_dirty(False)
        self.status_text.set(f"Saved {self.current_file}")
        return True

    def _load_example(self, name: str, confirm: bool = True) -> None:
        if name not in EXAMPLES:
            return
        if confirm and not self._confirm_discard_changes():
            return
        self._set_editor_content(EXAMPLES[name], file_path=None, dirty=False)
        self.example_name.set(name)
        self.status_text.set(f"Loaded example: {name}")

    def _set_editor_content(
        self, content: str, *, file_path: Path | None, dirty: bool
    ) -> None:
        self._loading_content = True
        try:
            self.editor.set_text(content)
        finally:
            self._loading_content = False
        self.current_file = file_path
        self._set_dirty(dirty)
        self._clear_results()
        self.editor.focus_editor()

    def _editor_changed(self) -> None:
        if not self._loading_content:
            self._set_dirty(True)
        self._update_cursor_status()

    def _set_dirty(self, value: bool) -> None:
        self.is_dirty = value
        filename = self.current_file.name if self.current_file else "Untitled.mc"
        dirty_marker = " *" if value else ""
        self.file_label.configure(text=filename + dirty_marker)
        self.title(f"{filename}{dirty_marker} — {APP_NAME}")

    def _confirm_discard_changes(self) -> bool:
        if not self.is_dirty:
            return True
        choice = messagebox.askyesnocancel(
            "Unsaved changes",
            "Save changes before continuing?",
        )
        if choice is None:
            return False
        if choice:
            return self._save_file()
        return True

    def _run_pipeline(self) -> None:
        self._start_compilation(MODE_ORDER)

    def _run_mode(self, mode: str) -> None:
        self._start_compilation((mode,))

    def _start_compilation(self, modes: tuple[str, ...]) -> None:
        if self.is_running:
            self.status_text.set("Compiler is already running")
            return
        if not self._refresh_compiler_state():
            messagebox.showerror(
                "Compiler unavailable",
                "Build the project first with 'make', then try again.\n\n"
                f"Expected compiler:\n{self.runner.compiler_path}",
            )
            return

        source = self.editor.get_text()
        if not source.strip():
            messagebox.showwarning("No source", "Enter MiniLang source code first.")
            return

        self.is_running = True
        self.pipeline_button.configure(state="disabled")
        for mode in modes:
            self._set_stage_state(mode, "running")
            self._set_output(mode, "Running compiler...\n")
        self.status_text.set(
            "Running " + ", ".join(MODE_LABELS[mode] for mode in modes) + "..."
        )

        worker = threading.Thread(
            target=self._compile_worker,
            args=(source, modes),
            name="minilang-compiler",
            daemon=True,
        )
        worker.start()
        self.after(60, self._poll_compiler_results)

    def _compile_worker(self, source: str, modes: tuple[str, ...]) -> None:
        results = self.runner.run_pipeline(source, modes)
        self._result_queue.put(results)

    def _poll_compiler_results(self) -> None:
        try:
            results = self._result_queue.get_nowait()
        except queue.Empty:
            self.after(60, self._poll_compiler_results)
            return
        self._show_compiler_results(results)

    def _show_compiler_results(self, results: dict[str, CompilerResult]) -> None:
        diagnostic_sections: list[str] = []
        total_duration = 0
        all_successful = True

        for mode, result in results.items():
            total_duration += result.duration_ms
            all_successful = all_successful and result.ok
            self._set_stage_state(mode, "success" if result.ok else "error")
            displayed_output = result.stdout.strip()
            if not displayed_output:
                displayed_output = (
                    "Compilation completed with no output."
                    if result.ok
                    else "Compilation failed. See the Diagnostics tab."
                )
            self._set_output(mode, displayed_output + "\n")

            command = " ".join(result.command) if result.command else "(not started)"
            status = "SUCCESS" if result.ok else f"FAILED (exit {result.return_code})"
            details = [
                f"[{MODE_LABELS[mode]}] {status} — {result.duration_ms} ms",
                f"Command: {command}",
            ]
            if result.stderr.strip():
                details.extend(("", result.stderr.strip()))
            diagnostic_sections.append("\n".join(details))

        self._set_output("diagnostics", "\n\n".join(diagnostic_sections) + "\n")
        if all_successful:
            self.status_text.set(f"Pipeline completed successfully in {total_duration} ms")
        else:
            self.status_text.set(
                f"Pipeline finished with errors in {total_duration} ms — see Diagnostics"
            )
            self.notebook.select(self.tab_frames["diagnostics"])

        self.is_running = False
        self.pipeline_button.configure(state="normal")

    def _set_stage_state(self, mode: str, state: str) -> None:
        colors = {
            "idle": ("#111d30", "#94a3b8"),
            "running": ("#3f2d12", "#fde68a"),
            "success": ("#12372a", "#86efac"),
            "error": ("#451a24", "#fda4af"),
        }
        background, foreground = colors[state]
        suffix = {
            "idle": "",
            "running": "  • running",
            "success": "  ✓",
            "error": "  ✕",
        }[state]
        self.stage_labels[mode].configure(
            text=MODE_LABELS[mode] + suffix,
            background=background,
            foreground=foreground,
        )

    def _set_output(self, name: str, content: str) -> None:
        widget = self.output_widgets[name]
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _clear_results(self) -> None:
        for mode in MODE_ORDER:
            self._set_stage_state(mode, "idle")
            self._set_output(mode, f"Run {MODE_LABELS[mode]} to see its output.\n")
        self._set_output(
            "diagnostics",
            "Compiler errors, exit codes, commands, and timing will appear here.\n",
        )

    def _update_cursor_status(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if not hasattr(self, "editor"):
            return
        line, column = self.editor.cursor_position()
        self.cursor_text.set(f"Ln {line}, Col {column}")

    def _close_requested(self) -> None:
        if self.is_running:
            if not messagebox.askyesno(
                "Compiler running", "The compiler is still running. Close anyway?"
            ):
                return
        if self._confirm_discard_changes():
            self.destroy()


def launch(project_root: Path | str, compiler_path: Path | str | None = None) -> None:
    """Construct and start the GUI event loop."""
    runner = CompilerRunner(project_root=project_root, compiler_path=compiler_path)
    app = MiniLangIDE(runner)
    app.mainloop()
