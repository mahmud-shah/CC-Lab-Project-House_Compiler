from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk

from .theme import COLORS


class ProjectExplorer(ttk.Frame):
    """Display editable project files without traversing generated caches."""

    IGNORED_DIRECTORIES = {
        ".git",
        ".idea",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        ".vscode",
        "__pycache__",
        "build",
        "build_win",
    }
    TEXT_EXTENSIONS = {
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".l",
        ".lex",
        ".md",
        ".mc",
        ".py",
        ".sh",
        ".txt",
        ".y",
        ".yaml",
        ".yml",
    }
    TEXT_FILENAMES = {
        ".gitignore",
        "CMakeLists.txt",
        "LICENSE",
        "Makefile",
    }

    def __init__(
        self,
        parent: tk.Misc,
        project_root: Path | str,
        on_open: Callable[[Path], None],
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=7)
        self.project_root = Path(project_root).resolve()
        self.on_open = on_open
        self._item_paths: dict[str, Path] = {}

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build_header()
        self._build_filter()
        self._build_tree()
        self.refresh()

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Surface.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header, text=self.project_root.name.upper(), style="SectionTitle.TLabel"
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Refresh",
            command=self.refresh,
            style="Compact.TButton",
        ).grid(row=0, column=1, padx=(4, 0))
        ttk.Button(
            header,
            text="Collapse",
            command=self.collapse_all,
            style="Compact.TButton",
        ).grid(row=0, column=2, padx=(4, 0))

    def _build_filter(self) -> None:
        self.filter_value = tk.StringVar()
        entry = ttk.Entry(self, textvariable=self.filter_value)
        entry.grid(row=1, column=0, sticky="ew", pady=(0, 7))
        self.filter_value.trace_add("write", lambda *_args: self.refresh())

    def _build_tree(self) -> None:
        tree_frame = ttk.Frame(self, style="Surface.TFrame")
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("root", foreground=COLORS.accent)
        self.tree.tag_configure("directory", foreground=COLORS.text)
        self.tree.tag_configure("source", foreground=COLORS.success)
        self.tree.tag_configure("document", foreground=COLORS.text_soft)
        self.tree.bind("<Double-1>", self._activate)
        self.tree.bind("<Return>", self._activate)
        self.tree.bind("<Right>", self._expand_selected)
        self.tree.bind("<Left>", self._collapse_selected)

        self.summary = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.summary,
            style="Muted.TLabel",
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(7, 0))

    def refresh(self) -> None:
        selected_path = self.selected_path()
        self.tree.delete(*self.tree.get_children())
        self._item_paths.clear()
        query = self.filter_value.get().strip().casefold()
        if query:
            self._populate_search(query)
        else:
            self._populate_hierarchy()
        if selected_path is not None:
            self.reveal(selected_path)

    def _populate_hierarchy(self) -> None:
        root_item = self.tree.insert(
            "", "end", text=f"▾  {self.project_root.name}", open=True, tags=("root",)
        )
        count = self._insert_directory(root_item, self.project_root)
        self.summary.set(f"{count} project files")

    def _insert_directory(self, parent_item: str, directory: Path) -> int:
        count = 0
        try:
            children = sorted(
                directory.iterdir(), key=lambda path: (path.is_file(), path.name.casefold())
            )
        except OSError:
            return 0
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in self.IGNORED_DIRECTORIES:
                    continue
                item = self.tree.insert(
                    parent_item,
                    "end",
                    text=f"▸  {child.name}",
                    open=False,
                    tags=("directory",),
                )
                count += self._insert_directory(item, child)
                if not self.tree.get_children(item):
                    self.tree.delete(item)
            elif self._is_text_file(child):
                tag = "source" if child.suffix.casefold() == ".mc" else "document"
                item = self.tree.insert(
                    parent_item, "end", text=f"   {child.name}", tags=(tag,)
                )
                self._item_paths[item] = child
                count += 1
        return count

    def _populate_search(self, query: str) -> None:
        matches: list[Path] = []
        for directory, names, files in os.walk(self.project_root):
            names[:] = sorted(
                name for name in names if name not in self.IGNORED_DIRECTORIES
            )
            for filename in files:
                path = Path(directory) / filename
                if path.is_symlink() or not self._is_text_file(path):
                    continue
                relative = path.relative_to(self.project_root).as_posix()
                if query in relative.casefold():
                    matches.append(path)
        for path in sorted(matches, key=lambda item: item.as_posix().casefold()):
            relative = path.relative_to(self.project_root).as_posix()
            tag = "source" if path.suffix.casefold() == ".mc" else "document"
            item = self.tree.insert("", "end", text=relative, tags=(tag,))
            self._item_paths[item] = path
        self.summary.set(f"{len(matches)} matching project files")

    def selected_path(self) -> Path | None:
        selection = self.tree.selection()
        return self._item_paths.get(selection[0]) if selection else None

    def reveal(self, path: Path) -> None:
        resolved = path.resolve()
        for item, candidate in self._item_paths.items():
            if candidate.resolve() != resolved:
                continue
            parent = self.tree.parent(item)
            while parent:
                self.tree.item(parent, open=True)
                parent = self.tree.parent(parent)
            self.tree.selection_set(item)
            self.tree.focus(item)
            self.tree.see(item)
            return

    def collapse_all(self) -> None:
        roots = self.tree.get_children("")
        for root in roots:
            self._set_open_recursive(root, False)
        if roots and not self.filter_value.get().strip():
            self.tree.item(roots[0], open=True)

    def focus_view(self) -> None:
        self.tree.focus_set()

    def _activate(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        path = self.selected_path()
        if path is not None:
            self.on_open(path)
            return
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            self.tree.item(item, open=not bool(self.tree.item(item, "open")))

    def _expand_selected(self, _event: tk.Event[tk.Misc]) -> str:
        selection = self.tree.selection()
        if selection:
            self.tree.item(selection[0], open=True)
        return "break"

    def _collapse_selected(self, _event: tk.Event[tk.Misc]) -> str:
        selection = self.tree.selection()
        if selection:
            self.tree.item(selection[0], open=False)
        return "break"

    def _set_open_recursive(self, item: str, opened: bool) -> None:
        self.tree.item(item, open=opened)
        for child in self.tree.get_children(item):
            self._set_open_recursive(child, opened)

    @classmethod
    def _is_text_file(cls, path: Path) -> bool:
        return path.name in cls.TEXT_FILENAMES or path.suffix.casefold() in cls.TEXT_EXTENSIONS
