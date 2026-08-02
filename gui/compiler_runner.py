from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MODE_FLAGS = {
    "tokens": "--tokens",
    "ast": "--ast",
    "symtab": "--symtab",
    "tac": "--tac",
}


@dataclass(frozen=True)
class CompilerResult:
    """Captured result of one compiler invocation."""

    mode: str
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.return_code == 0


class CompilerRunner:
    """Run the compiler without involving Tkinter or shell expansion."""

    def __init__(
        self,
        project_root: Path | str,
        compiler_path: Path | str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        configured_path = compiler_path or os.environ.get("MINILANG_COMPILER")
        if configured_path:
            candidate = Path(configured_path).expanduser()
            if not candidate.is_absolute():
                candidate = self.project_root / candidate
        else:
            candidate = self.project_root / "build" / "mcc"

        if os.name == "nt" and candidate.suffix.lower() != ".exe":
            windows_candidate = candidate.with_suffix(".exe")
            if windows_candidate.exists():
                candidate = windows_candidate

        self.compiler_path = candidate.resolve()
        self.timeout_seconds = timeout_seconds

    def validate(self) -> tuple[bool, str]:
        """Return whether the configured compiler is ready to execute."""
        if not self.compiler_path.is_file():
            return False, f"Compiler not found: {self.compiler_path}"
        if os.name != "nt" and not os.access(self.compiler_path, os.X_OK):
            return False, f"Compiler is not executable: {self.compiler_path}"
        return True, f"Compiler ready: {self.compiler_path}"

    def run(self, source: str, mode: str) -> CompilerResult:
        """Compile source in one supported inspection mode."""
        if mode not in MODE_FLAGS:
            raise ValueError(f"Unsupported compiler mode: {mode}")

        ready, message = self.validate()
        if not ready:
            return CompilerResult(
                mode=mode,
                command=(),
                return_code=127,
                stdout="",
                stderr=message,
                duration_ms=0,
            )

        with tempfile.TemporaryDirectory(prefix="minilang_gui_") as temp_dir:
            source_path = Path(temp_dir) / "editor_input.mc"
            source_path.write_text(source, encoding="utf-8")
            command = (
                str(self.compiler_path),
                str(source_path),
                MODE_FLAGS[mode],
            )
            started = time.perf_counter()
            try:
                completed = subprocess.run(
                    command,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout_seconds,
                    check=False,
                )
                return_code = completed.returncode
                stdout = completed.stdout
                stderr = completed.stderr
            except subprocess.TimeoutExpired as exc:
                return_code = 124
                stdout = self._decoded_output(exc.stdout)
                stderr = self._decoded_output(exc.stderr)
                if stderr and not stderr.endswith("\n"):
                    stderr += "\n"
                stderr += (
                    f"Compiler timed out after {self.timeout_seconds:g} seconds."
                )
            except OSError as exc:
                return_code = 126
                stdout = ""
                stderr = f"Could not start compiler: {exc}"

        duration_ms = round((time.perf_counter() - started) * 1000)
        return CompilerResult(
            mode=mode,
            command=command,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )

    def run_pipeline(
        self,
        source: str,
        modes: Iterable[str] = ("tokens", "ast", "symtab", "tac"),
    ) -> dict[str, CompilerResult]:
        """Run all requested views in a predictable order."""
        return {mode: self.run(source, mode) for mode in modes}

    @staticmethod
    def _decoded_output(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value