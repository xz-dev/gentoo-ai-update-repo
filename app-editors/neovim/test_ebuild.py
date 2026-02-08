#!/usr/bin/env python3
"""Smoke test for app-editors/neovim ebuild."""

import subprocess
import sys


def run_test(
    name: str, cmd: list[str], check_version: bool = False, expected_version: str = None
) -> bool:
    """Run a test command and check results."""
    print(f"Running: {name}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr

        if result.returncode != 0:
            print(f"  FAIL: Command exited with code {result.returncode}")
            if output:
                print(f"  Output:\n{output}")
            return False

        if check_version and expected_version:
            if expected_version not in output:
                print(
                    f"  FAIL: Expected version '{expected_version}' not found in output"
                )
                print(f"  Output:\n{output}")
                return False

        print(f"  PASS")
        return True
    except subprocess.TimeoutExpired:
        print(f"  FAIL: Command timed out")
        return False
    except Exception as e:
        print(f"  FAIL: Exception occurred: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_ebuild.py VERSION")
        sys.exit(1)

    version = sys.argv[1]
    print(f"Testing neovim-{version}")
    print("-" * 40)

    all_passed = True

    if not run_test(
        "nvim --version",
        ["nvim", "--version"],
        check_version=True,
        expected_version=version,
    ):
        all_passed = False

    if not run_test("nvim --help", ["nvim", "--help"]):
        all_passed = False

    if not run_test("nvim -h", ["nvim", "-h"]):
        all_passed = False

    print("-" * 40)
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
