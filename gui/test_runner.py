from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestResult:
    name: str
    category: str
    source_path: Path
    passed: bool
    return_code: int
    duration_ms: int
    command: tuple[str, ...]
    expected: str
    actual: str
    details: str

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


@dataclass(frozen=True)
class SuiteSummary:
    results: tuple[TestResult, ...]
    duration_ms: int
    cancelled: bool = False

    @property
    def passed(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed(self) -> int:
        return sum(not result.passed for result in self.results)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def ok(self) -> bool:
        return not self.cancelled and self.failed == 0 and self.total > 0


@dataclass(frozen=True)
class _TestSpec:
    name: str
    category: str
    source_path: Path
    expected_path: Path | None
    mode: str


ProgressCallback = Callable[[TestResult, int, int], None]


class RegressionSuiteRunner:
    """Run valid, invalid, and TAC golden checks without a shell script."""

    def __init__(
        self,
        project_root: Path | str,
        compiler_path: Path | str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.compiler_path = Path(compiler_path).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self.specs = tuple(self._discover_specs())

    def _discover_specs(self) -> list[_TestSpec]:
        specs: list[_TestSpec] = []
        valid_sources = sorted((self.project_root / "tests" / "valid").glob("*.mc"))
        example_sources = sorted((self.project_root / "examples").glob("*.mc"))
        for path in (*valid_sources, *example_sources):
            specs.append(
                _TestSpec(
                    name=self._relative(path),
                    category="Valid compilation",
                    source_path=path,
                    expected_path=None,
                    mode="valid",
                )
            )

        invalid_root = self.project_root / "tests" / "invalid"
        for phase in ("lexical", "syntax", "semantic"):
            phase_dir = invalid_root / phase
            for path in sorted(phase_dir.glob("*.mc")):
                specs.append(
                    _TestSpec(
                        name=self._relative(path),
                        category=f"{phase.title()} error",
                        source_path=path,
                        expected_path=phase_dir / "expected" / f"{path.stem}.err",
                        mode="invalid",
                    )
                )

        tac_dir = self.project_root / "tests" / "valid"
        for path in sorted(tac_dir.glob("tac_*.mc")):
            specs.append(
                _TestSpec(
                    name=self._relative(path),
                    category="TAC golden output",
                    source_path=path,
                    expected_path=tac_dir / "expected" / f"{path.stem}.tac",
                    mode="tac",
                )
            )
        return specs

    def run(
        self,
        progress: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> SuiteSummary:
        started = time.perf_counter()
        results: list[TestResult] = []
        total = len(self.specs)
        cancelled = False

        for index, spec in enumerate(self.specs, start=1):
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            result = self._run_spec(spec)
            results.append(result)
            if progress is not None:
                progress(result, index, total)

        return SuiteSummary(
            results=tuple(results),
            duration_ms=round((time.perf_counter() - started) * 1000),
            cancelled=cancelled,
        )

    def _run_spec(self, spec: _TestSpec) -> TestResult:
        relative_source = self._relative(spec.source_path)
        command_parts = [str(self.compiler_path), relative_source]
        if spec.mode == "tac":
            command_parts.append("--tac")
        command = tuple(command_parts)
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
            return self._failure_result(
                spec,
                command,
                124,
                round((time.perf_counter() - started) * 1000),
                "",
                self._decode_output(exc.stderr),
                f"Timed out after {self.timeout_seconds:g} seconds",
            )
        except OSError as exc:
            return self._failure_result(
                spec,
                command,
                126,
                round((time.perf_counter() - started) * 1000),
                "",
                str(exc),
                f"Could not start compiler: {exc}",
            )

        duration_ms = round((time.perf_counter() - started) * 1000)
        if spec.mode == "valid":
            passed = return_code == 0 and not stderr
            expected = "Exit code 0 and no standard-error output"
            actual = (
                f"Exit code: {return_code}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}"
            )
            details = "Compiled cleanly" if passed else "Valid program did not compile cleanly"
        else:
            expected, expected_error = self._read_expected(spec.expected_path)
            actual = stderr if spec.mode == "invalid" else stdout
            required_code = 1 if spec.mode == "invalid" else 0
            passed = (
                not expected_error
                and return_code == required_code
                and self._normalize(actual) == self._normalize(expected)
            )
            if passed:
                details = "Golden output matched"
            elif expected_error:
                details = expected_error
            elif return_code != required_code:
                details = f"Expected exit {required_code}, got {return_code}"
            else:
                details = "Output differs from golden file"

        return TestResult(
            name=spec.name,
            category=spec.category,
            source_path=spec.source_path,
            passed=passed,
            return_code=return_code,
            duration_ms=duration_ms,
            command=command,
            expected=expected,
            actual=actual,
            details=details,
        )

    def _failure_result(
        self,
        spec: _TestSpec,
        command: tuple[str, ...],
        return_code: int,
        duration_ms: int,
        stdout: str,
        stderr: str,
        details: str,
    ) -> TestResult:
        expected, _error = self._read_expected(spec.expected_path)
        actual = stderr or stdout
        return TestResult(
            name=spec.name,
            category=spec.category,
            source_path=spec.source_path,
            passed=False,
            return_code=return_code,
            duration_ms=duration_ms,
            command=command,
            expected=expected,
            actual=actual,
            details=details,
        )

    def _read_expected(self, path: Path | None) -> tuple[str, str]:
        if path is None:
            return "", "Expected-output path is missing"
        try:
            return path.read_text(encoding="utf-8"), ""
        except OSError as exc:
            return "", f"Could not read golden output: {exc}"

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.project_root).as_posix()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.replace("\r\n", "\n").replace("\r", "\n").rstrip()

    @staticmethod
    def _decode_output(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
