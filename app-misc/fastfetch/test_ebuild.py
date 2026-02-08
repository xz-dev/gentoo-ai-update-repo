#!/usr/bin/env python3
"""Smoke test for app-misc/fastfetch."""

import subprocess
import sys


def run_test(args, name):
    """Run a command and return success status."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=10)
        success = result.returncode == 0
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {name}")
        if not success:
            print(f"  Command: {' '.join(args)}")
            print(f"  Return code: {result.returncode}")
            if result.stderr:
                print(f"  Stderr: {result.stderr.strip()}")
        return success
    except subprocess.TimeoutExpired:
        print(f"[FAIL] {name} - timeout")
        return False
    except Exception as e:
        print(f"[FAIL] {name} - {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_ebuild.py VERSION")
        sys.exit(1)

    version = sys.argv[1]
    print(f"Testing fastfetch-{version}")

    tests_passed = 0
    total_tests = 0

    total_tests += 1
    if run_test(["fastfetch", "--version"], "fastfetch --version"):
        tests_passed += 1

    total_tests += 1
    if run_test(["fastfetch", "--help"], "fastfetch --help"):
        tests_passed += 1

    print(f"\nResults: {tests_passed}/{total_tests} tests passed")

    sys.exit(0 if tests_passed == total_tests else 1)


if __name__ == "__main__":
    main()
