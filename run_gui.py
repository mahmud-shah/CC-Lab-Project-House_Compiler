#!/usr/bin/env python3
"""Launch or self-test the MiniLang compiler GUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Desktop interface for the MiniLang compiler"
    )
    parser.add_argument(
        "--compiler",
        metavar="PATH",
        help="compiler executable (default: ./build/mcc or MINILANG_COMPILER)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="test all compiler views without opening a window",
    )
    return parser.parse_args()


def run_self_test(compiler_path: str | None) -> int:
    from gui.compiler_runner import CompilerRunner
    from gui.examples import DEFAULT_EXAMPLE, EXAMPLES

    runner = CompilerRunner(PROJECT_ROOT, compiler_path=compiler_path)
    ready, message = runner.validate()
    print(message)
    if not ready:
        return 2

    results = runner.run_pipeline(EXAMPLES[DEFAULT_EXAMPLE])
    failed = False
    for mode, result in results.items():
        status = "PASS" if result.ok and result.stdout.strip() else "FAIL"
        print(
            f"{status:4}  {mode:6}  exit={result.return_code}  "
            f"time={result.duration_ms}ms  output={len(result.stdout)} chars"
        )
        if status == "FAIL":
            failed = True
            if result.stderr.strip():
                print(result.stderr.strip())

    if failed:
        print("GUI backend self-test failed.")
        return 1
    print("GUI backend self-test passed.")
    return 0


def main() -> int:
    arguments = parse_arguments()
    if arguments.self_test:
        return run_self_test(arguments.compiler)

    try:
        from gui.app import launch

        launch(PROJECT_ROOT, compiler_path=arguments.compiler)
    except ModuleNotFoundError as exc:
        if exc.name == "tkinter":
            print(
                "Tkinter is not installed. On Ubuntu run:\n"
                "  sudo apt update && sudo apt install -y python3-tk",
                file=sys.stderr,
            )
            return 2
        raise
    except Exception as exc:
        if exc.__class__.__name__ == "TclError":
            print(
                "The GUI could not connect to a display. Start WSLg (Windows 11) "
                "or configure an X server, then run this command again.\n"
                f"Details: {exc}",
                file=sys.stderr,
            )
            return 2
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
