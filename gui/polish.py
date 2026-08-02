from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .theme import COLORS, ThemeFonts


class _Raster:
    def __init__(self, size: int = 16) -> None:
        self.size = size
        self.points: set[tuple[int, int]] = set()

    def point(self, x: int, y: int) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.points.add((x, y))

    def line(self, x1: int, y1: int, x2: int, y2: int) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        step_x = 1 if x1 < x2 else -1
        step_y = 1 if y1 < y2 else -1
        error = dx + dy
        while True:
            self.point(x1, y1)
            if x1 == x2 and y1 == y2:
                return
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x1 += step_x
            if doubled <= dx:
                error += dx
                y1 += step_y

    def rectangle(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.line(x1, y1, x2, y1)
        self.line(x2, y1, x2, y2)
        self.line(x2, y2, x1, y2)
        self.line(x1, y2, x1, y1)

    def fill_rectangle(self, x1: int, y1: int, x2: int, y2: int) -> None:
        for y in range(y1, y2 + 1):
            self.line(x1, y, x2, y)


def _new_icon(canvas: _Raster) -> None:
    canvas.rectangle(3, 1, 12, 14)
    canvas.line(9, 1, 12, 4)
    canvas.line(9, 1, 9, 4)
    canvas.line(9, 4, 12, 4)
    canvas.line(5, 8, 10, 8)
    canvas.line(5, 11, 10, 11)


def _open_icon(canvas: _Raster) -> None:
    canvas.line(1, 5, 5, 5)
    canvas.line(5, 5, 7, 3)
    canvas.line(7, 3, 12, 3)
    canvas.line(12, 3, 14, 6)
    canvas.line(2, 6, 14, 6)
    canvas.line(2, 6, 4, 13)
    canvas.line(4, 13, 12, 13)
    canvas.line(12, 13, 14, 6)


def _save_icon(canvas: _Raster) -> None:
    canvas.rectangle(2, 2, 13, 13)
    canvas.rectangle(5, 2, 11, 6)
    canvas.fill_rectangle(10, 3, 11, 5)
    canvas.rectangle(5, 9, 11, 13)


def _build_icon(canvas: _Raster) -> None:
    canvas.line(3, 2, 6, 5)
    canvas.line(5, 1, 8, 4)
    canvas.line(6, 5, 12, 11)
    canvas.line(10, 13, 13, 10)
    canvas.line(10, 13, 8, 11)
    canvas.line(13, 10, 11, 8)
    canvas.line(2, 3, 4, 1)


def _run_icon(canvas: _Raster) -> None:
    for x in range(4, 13):
        half_height = (12 - x) // 2
        canvas.line(x, 7 - half_height, x, 8 + half_height)


def _clear_icon(canvas: _Raster) -> None:
    canvas.line(3, 3, 12, 12)
    canvas.line(12, 3, 3, 12)
    canvas.line(4, 3, 12, 11)
    canvas.line(11, 3, 3, 11)


def _tests_icon(canvas: _Raster) -> None:
    canvas.rectangle(3, 2, 13, 14)
    canvas.line(1, 5, 3, 7)
    canvas.line(3, 7, 6, 3)
    canvas.line(7, 6, 11, 6)
    canvas.line(1, 10, 3, 12)
    canvas.line(3, 12, 6, 8)
    canvas.line(7, 11, 11, 11)


def _load_icon(canvas: _Raster) -> None:
    canvas.rectangle(2, 2, 11, 13)
    canvas.line(5, 5, 13, 5)
    canvas.line(10, 2, 13, 5)
    canvas.line(10, 8, 13, 5)


def create_toolbar_icons(root: tk.Misc) -> dict[str, tk.PhotoImage]:
    """Create small transparent icons without external image dependencies."""
    drawings: dict[str, tuple[str, Callable[[_Raster], None]]] = {
        "new": (COLORS.text_soft, _new_icon),
        "open": (COLORS.text_soft, _open_icon),
        "save": (COLORS.text_soft, _save_icon),
        "build": (COLORS.warning, _build_icon),
        "run": ("#ffffff", _run_icon),
        "clear": (COLORS.danger, _clear_icon),
        "tests": (COLORS.success, _tests_icon),
        "load": (COLORS.accent, _load_icon),
    }
    images: dict[str, tk.PhotoImage] = {}
    for name, (color, draw) in drawings.items():
        raster = _Raster()
        draw(raster)
        image = tk.PhotoImage(master=root, width=16, height=16)
        for x, y in raster.points:
            image.put(color, to=(x, y))
        images[name] = image
    return images


class ActivityIndicator(tk.Canvas):
    """Small non-blocking spinner used only while background work is active."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            width=24,
            height=24,
            background=COLORS.surface,
            highlightthickness=0,
        )
        self._frame = 0
        self._job: str | None = None
        self._running = False
        self._draw()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self._frame = 0
        self._draw()

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % 8
        self._draw()
        if self._running:
            self._job = self.after(90, self._tick)

    def _draw(self) -> None:
        self.delete("all")
        for index in range(8):
            angle = math.radians(index * 45 - 90)
            x = 12 + math.cos(angle) * 7
            y = 12 + math.sin(angle) * 7
            active = self._running and index == self._frame
            radius = 2.2 if active else 1.5
            color = COLORS.accent if active else COLORS.border
            self.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=color,
                outline="",
            )


class ToolTip:
    """Accessible delayed tooltip for compact toolbar controls."""

    def __init__(self, widget: ttk.Widget, text: str, fonts: ThemeFonts) -> None:
        self.widget = widget
        self.text = text
        self.fonts = fonts
        self._job: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: tk.Event[tk.Misc]) -> None:
        self._cancel()
        self._job = self.widget.after(550, self._show)

    def _show(self) -> None:
        if self._window is not None or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._window = tk.Toplevel(self.widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._window,
            text=self.text,
            background=COLORS.surface_raised,
            foreground=COLORS.text,
            highlightbackground=COLORS.border,
            highlightthickness=1,
            padx=8,
            pady=5,
            font=(self.fonts.ui, 8),
        ).pack()

    def _hide(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None

    def _cancel(self) -> None:
        if self._job is not None:
            self.widget.after_cancel(self._job)
            self._job = None
