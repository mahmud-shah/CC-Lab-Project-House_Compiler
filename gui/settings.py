from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


GEOMETRY_PATTERN = re.compile(r"^\d+x\d+(?:[+-]\d+){2}$")


@dataclass(frozen=True)
class AppSettings:
    geometry: str = "1560x920+40+40"
    main_sash: int = 285
    workspace_sash: int = 550
    selected_tab: int = 0


class SettingsStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else self.default_path()

    @staticmethod
    def default_path() -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "minilang-compiler-studio" / "settings.json"

    def load(self) -> AppSettings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return AppSettings()
        if not isinstance(data, dict):
            return AppSettings()

        defaults = AppSettings()
        geometry = data.get("geometry", defaults.geometry)
        if not isinstance(geometry, str) or GEOMETRY_PATTERN.fullmatch(geometry) is None:
            geometry = defaults.geometry
        return AppSettings(
            geometry=geometry,
            main_sash=self._bounded_int(data.get("main_sash"), defaults.main_sash, 180, 700),
            workspace_sash=self._bounded_int(
                data.get("workspace_sash"), defaults.workspace_sash, 220, 1200
            ),
            selected_tab=self._bounded_int(
                data.get("selected_tab"), defaults.selected_tab, 0, 20
            ),
        )

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _bounded_int(value: object, fallback: int, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return fallback
        return max(minimum, min(value, maximum))
