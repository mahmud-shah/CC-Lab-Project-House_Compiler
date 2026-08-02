from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .test_runner import SuiteSummary, TestResult
from .theme import COLORS, ThemeFonts


class TestDashboard(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        on_run: Callable[[], None],
        on_cancel: Callable[[], None],
        on_open_source: Callable[[TestResult], None],
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=6)
        self.fonts = fonts
        self.on_run = on_run
        self.on_cancel = on_cancel
        self.on_open_source = on_open_source
        self.results: list[TestResult] = []
        self._tree_results: dict[str, TestResult] = {}
        self.expected_total = 42

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_toolbar()
        self._build_metrics()
        self._build_progress()
        self._build_result_area()

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self, style="Surface.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        toolbar.columnconfigure(5, weight=1)
        self.run_button = ttk.Button(
            toolbar,
            text="Run All 42 Checks",
            command=self.on_run,
            style="Accent.TButton",
        )
        self.run_button.grid(row=0, column=0, padx=(0, 5))
        self.stop_button = ttk.Button(
            toolbar,
            text="Stop",
            command=self.on_cancel,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, padx=(0, 12))
        ttk.Label(toolbar, text="Show", style="Muted.TLabel").grid(
            row=0, column=2, padx=(0, 5)
        )
        self.filter_value = tk.StringVar(value="All results")
        filter_box = ttk.Combobox(
            toolbar,
            textvariable=self.filter_value,
            values=(
                "All results",
                "Passed",
                "Failed",
                "Valid compilation",
                "Lexical error",
                "Syntax error",
                "Semantic error",
                "TAC golden output",
            ),
            state="readonly",
            width=21,
        )
        filter_box.grid(row=0, column=3)
        filter_box.bind("<<ComboboxSelected>>", lambda _event: self._populate())
        self.suite_state = tk.StringVar(value="Regression suite has not been run")
        ttk.Label(toolbar, textvariable=self.suite_state, style="Muted.TLabel").grid(
            row=0, column=5, sticky="e", padx=(10, 4)
        )

    def _build_metrics(self) -> None:
        metrics = ttk.Frame(self, style="Surface.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(0, 7))
        for column in range(4):
            metrics.columnconfigure(column, weight=1)

        self.total_value = tk.StringVar(value="0 / 42")
        self.passed_value = tk.StringVar(value="0")
        self.failed_value = tk.StringVar(value="0")
        self.duration_value = tk.StringVar(value="--")
        cards = (
            ("COMPLETED", self.total_value, COLORS.accent),
            ("PASSED", self.passed_value, COLORS.success),
            ("FAILED", self.failed_value, COLORS.danger),
            ("DURATION", self.duration_value, COLORS.warning),
        )
        for column, (caption, variable, color) in enumerate(cards):
            card = tk.Frame(
                metrics,
                background=COLORS.surface_raised,
                highlightbackground=COLORS.border,
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0, 6 if column < len(cards) - 1 else 0),
            )
            tk.Label(
                card,
                text=caption,
                background=COLORS.surface_raised,
                foreground=COLORS.muted,
                font=(self.fonts.ui, 8, "bold"),
            ).pack(anchor="w", padx=10, pady=(7, 0))
            tk.Label(
                card,
                textvariable=variable,
                background=COLORS.surface_raised,
                foreground=color,
                font=(self.fonts.ui, 14, "bold"),
            ).pack(anchor="w", padx=10, pady=(0, 7))

    def _build_progress(self) -> None:
        self.progress = ttk.Progressbar(self, mode="determinate", maximum=42)
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 7))

    def _build_result_area(self) -> None:
        pane = ttk.Panedwindow(self, orient="vertical")
        pane.grid(row=3, column=0, sticky="nsew")

        table_frame = ttk.Frame(pane, style="Surface.TFrame")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("status", "category", "source", "exit", "duration", "details")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        definitions = {
            "status": ("Status", 75, "center"),
            "category": ("Category", 145, "w"),
            "source": ("Source", 390, "w"),
            "exit": ("Exit", 55, "center"),
            "duration": ("Time", 75, "center"),
            "details": ("Details", 260, "w"),
        }
        for name, (caption, width, anchor) in definitions.items():
            self.tree.heading(name, text=caption)
            self.tree.column(
                name,
                width=width,
                anchor=anchor,
                stretch=name in {"source", "details"},
            )
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.tag_configure("pass", foreground=COLORS.success)
        self.tree.tag_configure("fail", foreground=COLORS.danger)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", self._open_selected)
        self.tree.bind("<Return>", self._open_selected)

        detail_frame = ttk.Frame(pane, style="Surface.TFrame", padding=(0, 6, 0, 0))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)
        ttk.Label(
            detail_frame,
            text="SELECTED TEST DETAILS",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.detail = tk.Text(
            detail_frame,
            height=8,
            wrap="none",
            state="disabled",
            background=COLORS.editor,
            foreground=COLORS.text_soft,
            selectbackground=COLORS.selection,
            relief="flat",
            padx=10,
            pady=8,
            font=(self.fonts.mono, 9),
        )
        detail_scroll = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.detail.yview
        )
        self.detail.configure(yscrollcommand=detail_scroll.set)
        self.detail.grid(row=1, column=0, sticky="nsew")
        detail_scroll.grid(row=1, column=1, sticky="ns")

        pane.add(table_frame, weight=3)
        pane.add(detail_frame, weight=2)

    def begin(self, total: int) -> None:
        self.results.clear()
        self._tree_results.clear()
        self.tree.delete(*self.tree.get_children())
        self.expected_total = total
        self.progress.configure(maximum=max(total, 1), value=0)
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.suite_state.set("Running regression suite...")
        self._update_metrics(0)
        self._set_detail("Tests are running. Select a completed row for details.")

    def add_result(self, result: TestResult, index: int, total: int) -> None:
        self.results.append(result)
        self.expected_total = total
        self.progress.configure(maximum=max(total, 1), value=index)
        if self._matches_filter(result):
            self._insert_result(result)
        self._update_metrics(index)
        self.suite_state.set(f"Running check {index} of {total}: {result.name}")

    def finish(self, summary: SuiteSummary) -> None:
        self.run_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.duration_value.set(f"{summary.duration_ms} ms")
        if summary.cancelled:
            self.suite_state.set(
                f"Cancelled after {summary.total} of {self.expected_total} checks"
            )
        elif summary.ok:
            self.suite_state.set(f"All {summary.total} regression checks passed")
        else:
            self.suite_state.set(
                f"Completed with {summary.failed} failure{'s' if summary.failed != 1 else ''}"
            )

    def cancel_pending(self) -> None:
        self.stop_button.configure(state="disabled")
        self.suite_state.set("Cancellation requested - finishing current check...")

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _populate(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._tree_results.clear()
        for result in self.results:
            if self._matches_filter(result):
                self._insert_result(result)

    def _insert_result(self, result: TestResult) -> None:
        item = self.tree.insert(
            "",
            "end",
            values=(
                result.status,
                result.category,
                result.name,
                result.return_code,
                f"{result.duration_ms} ms",
                result.details,
            ),
            tags=("pass" if result.passed else "fail",),
        )
        self._tree_results[item] = result

    def _matches_filter(self, result: TestResult) -> bool:
        selected = self.filter_value.get()
        if selected == "All results":
            return True
        if selected == "Passed":
            return result.passed
        if selected == "Failed":
            return not result.passed
        return result.category == selected

    def _update_metrics(self, completed: int) -> None:
        passed = sum(result.passed for result in self.results)
        failed = len(self.results) - passed
        self.total_value.set(f"{completed} / {self.expected_total}")
        self.passed_value.set(str(passed))
        self.failed_value.set(str(failed))
        if completed < self.expected_total:
            self.duration_value.set("running")

    def _selection_changed(self, _event: tk.Event[tk.Misc]) -> None:
        result = self._selected_result()
        if result is None:
            return
        command = " ".join(result.command)
        content = (
            f"{result.status}  {result.category}\n"
            f"Source: {result.name}\n"
            f"Command: {command}\n"
            f"Exit code: {result.return_code}\n"
            f"Duration: {result.duration_ms} ms\n"
            f"Details: {result.details}\n\n"
            f"EXPECTED\n{'=' * 72}\n{result.expected}\n\n"
            f"ACTUAL\n{'=' * 72}\n{result.actual}"
        )
        self._set_detail(content)

    def _open_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        result = self._selected_result()
        if result is not None:
            self.on_open_source(result)

    def _selected_result(self) -> TestResult | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self._tree_results.get(selection[0])

    def _set_detail(self, content: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", content)
        self.detail.configure(state="disabled")
