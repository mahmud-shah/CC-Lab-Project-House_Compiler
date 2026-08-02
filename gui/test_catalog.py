from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestCase:
    key: str
    label: str
    source_path: Path
    group: tuple[str, ...]
    kind: str
    phase: str | None = None
    expected_path: Path | None = None

    @property
    def relative_path(self) -> str:
        return self.key


class TestCatalog:
    """Read-only catalogue generated from examples/ and tests/."""

    def __init__(self, project_root: Path | str) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.cases = tuple(self._discover())

    def _discover(self) -> list[TestCase]:
        cases: list[TestCase] = []

        examples_dir = self.project_root / "examples"
        for path in sorted(examples_dir.glob("*.mc")):
            cases.append(self._make_case(path, ("Examples",), "example"))

        valid_dir = self.project_root / "tests" / "valid"
        for path in sorted(valid_dir.glob("*.mc")):
            expected = valid_dir / "expected" / f"{path.stem}.tac"
            cases.append(
                self._make_case(
                    path,
                    ("Valid Tests", self._valid_subgroup(path.stem)),
                    "valid",
                    expected_path=expected if expected.is_file() else None,
                )
            )

        invalid_dir = self.project_root / "tests" / "invalid"
        for phase in ("lexical", "syntax", "semantic"):
            phase_dir = invalid_dir / phase
            for path in sorted(phase_dir.glob("*.mc")):
                expected = phase_dir / "expected" / f"{path.stem}.err"
                cases.append(
                    self._make_case(
                        path,
                        ("Invalid Tests", phase.title()),
                        "invalid",
                        phase=phase,
                        expected_path=expected if expected.is_file() else None,
                    )
                )
        return cases

    def _make_case(
        self,
        path: Path,
        group: tuple[str, ...],
        kind: str,
        *,
        phase: str | None = None,
        expected_path: Path | None = None,
    ) -> TestCase:
        return TestCase(
            key=path.relative_to(self.project_root).as_posix(),
            label=self._humanize(path.stem),
            source_path=path,
            group=group,
            kind=kind,
            phase=phase,
            expected_path=expected_path,
        )

    @staticmethod
    def _humanize(stem: str) -> str:
        words = stem.replace("_", " ").replace("-", " ").split()
        acronyms = {"tac": "TAC", "ast": "AST", "cfg": "CFG"}
        return " ".join(acronyms.get(word.casefold(), word.capitalize()) for word in words)

    @staticmethod
    def _valid_subgroup(stem: str) -> str:
        if stem.startswith("tac_"):
            return "TAC Generation"
        if "lexer" in stem:
            return "Lexical Analysis"
        if "scope" in stem or "semantic" in stem:
            return "Semantic Analysis"
        return "Language Features"

    def filtered(self, query: str) -> tuple[TestCase, ...]:
        normalized = query.strip().casefold()
        if not normalized:
            return self.cases
        return tuple(
            case
            for case in self.cases
            if normalized in case.label.casefold()
            or normalized in case.relative_path.casefold()
            or any(normalized in part.casefold() for part in case.group)
        )

    @property
    def valid_count(self) -> int:
        return sum(case.kind in {"valid", "example"} for case in self.cases)

    @property
    def invalid_count(self) -> int:
        return sum(case.kind == "invalid" for case in self.cases)

    @property
    def summary(self) -> str:
        return (
            f"{len(self.cases)} source files  |  "
            f"{self.valid_count} valid/example  |  {self.invalid_count} invalid"
        )
