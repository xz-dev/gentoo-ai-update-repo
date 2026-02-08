#!/usr/bin/env python3
"""
Black-box smoke test for app-misc/fastfetch.
Usage: python3 test_ebuild.py VERSION
"""

import os
import subprocess
import sys


def run_test(name, func):
    """Run a test and print result."""
    try:
        result = func()
        if result:
            print(f"[PASS] {name}")
            return True
        else:
            print(f"[FAIL] {name}")
            return False
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False


def test_version_output(version):
    """Verify version string appears in program output."""
    try:
        result = subprocess.run(
            ["fastfetch", "--version"], capture_output=True, text=True, timeout=10
        )
        output = result.stdout + result.stderr
        return version in output
    except Exception:
        return False


def test_fastfetch_runs(version):
    """Test that fastfetch executes and produces output."""
    try:
        result = subprocess.run(
            ["fastfetch"], capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return False
        output = result.stdout + result.stderr
        return len(output) > 0
    except Exception:
        return False


def test_binary_installed():
    """Verify the fastfetch binary is installed."""
    return os.path.isfile("/usr/bin/fastfetch")


def test_man_page_installed():
    """Check if man page exists (optional)."""
    man_paths = [
        "/usr/share/man/man1/fastfetch.1.gz",
        "/usr/share/man/man1/fastfetch.1",
    ]
    return any(os.path.isfile(p) for p in man_paths)


def test_fastfetch_help():
    """Test that help output works."""
    try:
        result = subprocess.run(
            ["fastfetch", "--help"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False
        output = result.stdout + result.stderr
        return len(output) > 0 and "fastfetch" in output.lower()
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_ebuild.py VERSION")
        sys.exit(1)

    version = sys.argv[1]
    tests = [
        ("Binary installed", test_binary_installed),
        ("Version output", lambda: test_version_output(version)),
        ("Help output", test_fastfetch_help),
        ("Runs and produces output", lambda: test_fastfetch_runs(version)),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        if run_test(name, test_func):
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
