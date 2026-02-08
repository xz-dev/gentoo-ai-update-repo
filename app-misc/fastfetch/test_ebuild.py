#!/usr/bin/env python3
"""
Black-box smoke test for app-misc/fastfetch.
Usage: python3 test_ebuild.py VERSION
"""

import subprocess
import sys
import os


def run_test(name, test_func):
    """Run a test and print result."""
    try:
        result = test_func()
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
    """Test that VERSION string appears in fastfetch output."""
    result = subprocess.run(["fastfetch", "--version"], capture_output=True, text=True)
    output = result.stdout + result.stderr
    if version in output:
        return True
    return False


def test_core_functionality():
    """Test that fastfetch runs and produces output."""
    result = subprocess.run(["fastfetch"], capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout + result.stderr
        if len(output) > 50 and "OS:" in output:
            return True
    return False


def test_version_help_output(version):
    """Test that VERSION appears in help output."""
    result = subprocess.run(["fastfetch", "--help"], capture_output=True, text=True)
    output = result.stdout + result.stderr
    if version in output:
        return True
    return False


def test_binary_exists():
    """Test that fastfetch binary exists."""
    return os.path.exists("/usr/bin/fastfetch")


def test_man_page_exists():
    """Test that fastfetch man page exists."""
    man_paths = [
        "/usr/share/man/man1/fastfetch.1",
        "/usr/share/man/man1/fastfetch.1.gz",
    ]
    return any(os.path.exists(p) for p in man_paths)


def test_doc_files_exist():
    """Test that doc files exist (license, readme, etc.)."""
    doc_dir = "/usr/share/doc/fastfetch"
    if os.path.exists(doc_dir):
        return True
    return False


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} VERSION")
        sys.exit(1)

    version = sys.argv[1]

    tests = [
        ("Binary exists", test_binary_exists),
        ("Version in --version output", lambda: test_version_output(version)),
        ("Version in --help output", lambda: test_version_help_output(version)),
        ("Core functionality (run and produce output)", test_core_functionality),
        ("Man page exists", test_man_page_exists),
        ("Documentation exists", test_doc_files_exist),
    ]

    results = []
    for name, test_func in tests:
        results.append(run_test(name, test_func))

    if all(results):
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print(f"\n{results.count(False)} test(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
