from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .theme import COLORS, ThemeFonts


class PipelineStrip(tk.Frame):
    """Compact, color-coded view of the required compiler phases."""

    PHASES = (
        ("lexer", "Lexer"),
        ("parser", "Parser / AST"),
        ("semantic", "Semantic / Symbols"),
        ("tac", "TAC"),
    )
    STATE_COLORS = {
        "idle": (COLORS.surface_raised, COLORS.muted),
        "running": (COLORS.warning_dark, COLORS.warning),
        "success": (COLORS.success_dark, COLORS.success),
        "error": (COLORS.danger_dark, COLORS.danger),
    }

    def __init__(self, parent: tk.Misc, fonts: ThemeFonts) -> None:
        super().__init__(parent, background=COLORS.surface, highlightthickness=0)
        self.fonts = fonts
        self.labels: dict[str, tk.Label] = {}

        title = tk.Label(
            self,
            text="PIPELINE",
            background=COLORS.surface,
            foreground=COLORS.text,
            font=(fonts.ui, 9, "bold"),
            padx=8,
        )
        title.pack(side="left", padx=(0, 8))

        for index, (phase, caption) in enumerate(self.PHASES):
            label = tk.Label(
                self,
                text=f"{caption}  IDLE",
                background=COLORS.surface_raised,
                foreground=COLORS.muted,
                font=(fonts.ui, 8, "bold"),
                padx=10,
                pady=6,
                cursor="hand2",
            )
            label.pack(side="left")
            self.labels[phase] = label
            if index < len(self.PHASES) - 1:
                tk.Label(
                    self,
                    text="  >  ",
                    background=COLORS.surface,
                    foreground=COLORS.border,
                    font=(fonts.mono, 9, "bold"),
                ).pack(side="left")

    def bind_phase(self, phase: str, callback: object) -> None:
        self.labels[phase].bind("<Button-1>", callback)

    def set_state(self, phase: str, state: str) -> None:
        background, foreground = self.STATE_COLORS[state]
        caption = dict(self.PHASES)[phase]
        marker = {
            "idle": "IDLE",
            "running": "RUNNING",
            "success": "PASSED",
            "error": "FAILED",
        }[state]
        self.labels[phase].configure(
            text=f"{caption}  {marker}",
            background=background,
            foreground=foreground,
        )

    def reset(self) -> None:
        for phase, _caption in self.PHASES:
            self.set_state(phase, "idle")


class OutputView(ttk.Frame):
    """Read-only output surface with copy, save, and clear actions."""

    def __init__(
        self,
        parent: tk.Misc,
        fonts: ThemeFonts,
        *,
        save_extension: str = ".txt",
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=6)
        self.save_extension = save_extension
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        actions = ttk.Frame(self, style="Surface.TFrame")
        actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Button(
            actions, text="Copy All", command=self.copy_all, style="Toolbar.TButton"
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            actions, text="Save As...", command=self.save_as, style="Toolbar.TButton"
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            actions, text="Clear", command=self.clear, style="Toolbar.TButton"
        ).pack(side="left")

        self.text = tk.Text(
            self,
            wrap="none",
            state="disabled",
            background=COLORS.editor,
            foreground=COLORS.text_soft,
            insertbackground=COLORS.accent,
            selectbackground=COLORS.selection,
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=10,
            font=(fonts.mono, 10),
        )
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.text.grid(row=1, column=0, sticky="nsew")
        vertical.grid(row=1, column=1, sticky="ns")
        horizontal.grid(row=2, column=0, sticky="ew")

        self.text.tag_configure("error", foreground=COLORS.danger)
        self.text.tag_configure("success", foreground=COLORS.success)
        self.text.tag_configure("warning", foreground=COLORS.warning)
        self.text.tag_configure("heading", foreground=COLORS.accent)

    def set_content(self, content: str, tag: str | None = None) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if content:
            self.text.insert("1.0", content, tag or ())
        self.text.configure(state="disabled")

    def append(self, content: str, tag: str | None = None) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", content, tag or ())
        self.text.see("end")
        self.text.configure(state="disabled")

    def get_content(self) -> str:
        return self.text.get("1.0", "end-1c")

    def clear(self) -> None:
        self.set_content("")

    def copy_all(self) -> None:
        content = self.get_content()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)

    def save_as(self) -> None:
        content = self.get_content()
        if not content:
            messagebox.showinfo("Nothing to save", "This output panel is empty.")
            return
        selected = filedialog.asksaveasfilename(
            title="Save compiler output",
            defaultextension=self.save_extension,
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            Path(selected).write_text(content, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save output:\n\n{exc}")
