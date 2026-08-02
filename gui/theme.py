from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class Palette:
    background: str = "#07101d"
    background_deep: str = "#050a13"
    surface: str = "#0c1728"
    surface_raised: str = "#111f33"
    surface_hover: str = "#172a43"
    border: str = "#263a55"
    border_soft: str = "#182940"
    text: str = "#e6eef9"
    text_soft: str = "#b7c7da"
    muted: str = "#8093ac"
    accent: str = "#38bdf8"
    accent_active: str = "#0ea5e9"
    accent_dark: str = "#0c4a6e"
    success: str = "#34d399"
    success_dark: str = "#123c32"
    warning: str = "#fbbf24"
    warning_dark: str = "#493814"
    danger: str = "#fb7185"
    danger_dark: str = "#4a1d2a"
    violet: str = "#a78bfa"
    editor: str = "#08111f"
    editor_gutter: str = "#060d18"
    selection: str = "#164e63"


@dataclass(frozen=True)
class ThemeFonts:
    ui: str
    mono: str


COLORS = Palette()


def _choose_font(root: tk.Misc, candidates: tuple[str, ...], fallback: str) -> str:
    available = {name.casefold(): name for name in tkfont.families(root)}
    for candidate in candidates:
        if candidate.casefold() in available:
            return available[candidate.casefold()]
    return fallback


def apply_theme(root: tk.Misc) -> ThemeFonts:
    """Configure ttk and classic Tk widgets with one coherent IDE theme."""
    fonts = ThemeFonts(
        ui=_choose_font(root, ("Inter", "Segoe UI", "Ubuntu"), "TkDefaultFont"),
        mono=_choose_font(
            root,
            ("Cascadia Code", "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono"),
            "TkFixedFont",
        ),
    )

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    root.option_add("*Font", (fonts.ui, 10))
    root.option_add("*tearOff", False)
    root.option_add("*Menu.background", COLORS.surface_raised)
    root.option_add("*Menu.foreground", COLORS.text)
    root.option_add("*Menu.activeBackground", COLORS.accent_dark)
    root.option_add("*Menu.activeForeground", "#ffffff")
    root.option_add("*Menu.borderWidth", 0)

    style.configure(".", background=COLORS.background, foreground=COLORS.text)
    style.configure("App.TFrame", background=COLORS.background)
    style.configure("Surface.TFrame", background=COLORS.surface)
    style.configure("Raised.TFrame", background=COLORS.surface_raised)
    style.configure("Toolbar.TFrame", background=COLORS.surface, relief="flat")
    style.configure("Editor.TFrame", background=COLORS.editor)

    style.configure(
        "Title.TLabel",
        background=COLORS.background,
        foreground=COLORS.text,
        font=(fonts.ui, 17, "bold"),
    )
    style.configure(
        "Subtitle.TLabel",
        background=COLORS.background,
        foreground=COLORS.muted,
        font=(fonts.ui, 9),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=COLORS.surface,
        foreground=COLORS.text,
        font=(fonts.ui, 10, "bold"),
    )
    style.configure(
        "RaisedTitle.TLabel",
        background=COLORS.surface_raised,
        foreground=COLORS.text,
        font=(fonts.ui, 10, "bold"),
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS.surface,
        foreground=COLORS.muted,
        font=(fonts.ui, 9),
    )
    style.configure(
        "Status.TLabel",
        background=COLORS.background,
        foreground=COLORS.text_soft,
        font=(fonts.ui, 9),
    )

    style.configure(
        "Toolbar.TButton",
        background=COLORS.surface_raised,
        foreground=COLORS.text_soft,
        bordercolor=COLORS.border,
        lightcolor=COLORS.surface_raised,
        darkcolor=COLORS.surface_raised,
        padding=(13, 8),
        font=(fonts.ui, 9),
        relief="flat",
    )
    style.map(
        "Toolbar.TButton",
        background=[("active", COLORS.surface_hover), ("pressed", COLORS.accent_dark)],
        foreground=[("active", "#ffffff"), ("disabled", COLORS.muted)],
        bordercolor=[("focus", COLORS.accent), ("active", COLORS.accent)],
    )
    style.configure(
        "Accent.TButton",
        background=COLORS.accent_active,
        foreground="#ffffff",
        bordercolor=COLORS.accent,
        lightcolor=COLORS.accent_active,
        darkcolor=COLORS.accent_active,
        padding=(15, 8),
        font=(fonts.ui, 9, "bold"),
        relief="flat",
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS.accent), ("pressed", COLORS.accent_dark)],
        foreground=[("disabled", COLORS.muted)],
    )
    style.configure(
        "Danger.TButton",
        background=COLORS.danger_dark,
        foreground=COLORS.danger,
        bordercolor=COLORS.danger_dark,
        padding=(12, 7),
        relief="flat",
    )
    style.map("Danger.TButton", background=[("active", "#652538")])

    style.configure(
        "Treeview",
        background=COLORS.surface,
        fieldbackground=COLORS.surface,
        foreground=COLORS.text_soft,
        bordercolor=COLORS.border_soft,
        rowheight=28,
        relief="flat",
        font=(fonts.ui, 9),
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS.accent_dark)],
        foreground=[("selected", "#ffffff")],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS.surface_raised,
        foreground=COLORS.text,
        bordercolor=COLORS.border,
        padding=(8, 7),
        font=(fonts.ui, 9, "bold"),
    )

    style.configure(
        "TNotebook",
        background=COLORS.surface,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=COLORS.surface_raised,
        foreground=COLORS.muted,
        borderwidth=0,
        padding=(14, 8),
        font=(fonts.ui, 9),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS.accent_dark), ("active", COLORS.surface_hover)],
        foreground=[("selected", "#ffffff"), ("active", COLORS.text)],
    )

    style.configure(
        "TEntry",
        fieldbackground=COLORS.background_deep,
        foreground=COLORS.text,
        insertcolor=COLORS.accent,
        bordercolor=COLORS.border,
        lightcolor=COLORS.border,
        darkcolor=COLORS.border,
        padding=(8, 6),
    )
    style.map("TEntry", bordercolor=[("focus", COLORS.accent)])
    style.configure(
        "TCombobox",
        fieldbackground=COLORS.background_deep,
        background=COLORS.surface_raised,
        foreground=COLORS.text,
        arrowcolor=COLORS.accent,
        bordercolor=COLORS.border,
        padding=(6, 5),
    )

    style.configure(
        "Vertical.TScrollbar",
        background=COLORS.surface_raised,
        troughcolor=COLORS.background_deep,
        bordercolor=COLORS.background_deep,
        arrowcolor=COLORS.muted,
        width=12,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=COLORS.surface_raised,
        troughcolor=COLORS.background_deep,
        bordercolor=COLORS.background_deep,
        arrowcolor=COLORS.muted,
    )
    style.configure("TPanedwindow", background=COLORS.border_soft, sashwidth=5)
    style.configure("TSeparator", background=COLORS.border)
    return fonts
