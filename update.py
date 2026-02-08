#!/usr/bin/env python3
"""
Gentoo AI Ebuild Update Orchestrator

Usage:
    python3 update.py app-editors/neovim
    python3 update.py app-editors/neovim::gentoo
    python3 update.py --help

This script delegates all "smart" work to opencode AI agents.
It only handles file I/O, subprocess calls, and decision flow.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

# ─── Constants ────────────────────────────────────────────────────────────────

REPO_DIR = Path("/var/db/repos/gentoo-ai-update-repo")
SYSTEM_REPOS_DIR = Path("/var/db/repos")
AI_MODEL_WEB = "opencode/kimi-k2.5-free"  # Good at web/API info, version checking
AI_MODEL_CODE = "opencode/minimax-m2.1-free"  # Good at writing code, ebuilds, tests
MAX_VERSION_RETRIES = 5
CONTAINER_IMAGE = "docker.io/gentoo/stage3"

# ─── Helpers ──────────────────────────────────────────────────────────────────


def log(msg: str, level: str = "INFO"):
    colors = {
        "INFO": "\033[36m",
        "OK": "\033[32m",
        "WARN": "\033[33m",
        "ERR": "\033[31m",
        "AI": "\033[35m",
    }
    reset = "\033[0m"
    c = colors.get(level, "")
    print(f"{c}[{level}]{reset} {msg}", file=sys.stderr)


def run_cmd(
    cmd: list[str], cwd: str | None = None, capture: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return result. Does NOT raise on failure."""
    log(f"$ {' '.join(cmd)}")
    if capture:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    else:
        # Stream output to terminal in real-time, capture nothing
        r = subprocess.run(cmd, cwd=cwd)
        r = subprocess.CompletedProcess(cmd, r.returncode, stdout="", stderr="")
    return r


def run_ai(
    prompt: str,
    cwd: str,
    files: list[str] | None = None,
    model: str = AI_MODEL_WEB,
) -> subprocess.CompletedProcess:
    """Invoke opencode AI agent and return result. Output streams to terminal."""
    cmd = ["opencode", "run", "-m", model]
    if files:
        for f in files:
            cmd.extend(["-f", f])
    cmd.append(prompt)
    log(f"AI invocation in {cwd}", "AI")
    log(f"  prompt: {prompt[:120]}{'...' if len(prompt) > 120 else ''}", "AI")
    return run_cmd(cmd, cwd=cwd, capture=False)


def parse_package_atom(atom: str) -> tuple[str, str, str | None]:
    """Parse 'cat/pkg' or 'cat/pkg::repo' → (category, package, repo_hint)."""
    repo_hint = None
    if "::" in atom:
        atom, repo_hint = atom.split("::", 1)
    parts = atom.strip("/").split("/")
    if len(parts) != 2:
        log(f"Invalid package atom: {atom}. Expected format: category/package", "ERR")
        sys.exit(1)
    return parts[0], parts[1], repo_hint


def find_source_package(
    category: str, package: str, repo_hint: str | None
) -> Path | None:
    """Find package directory in system repos."""
    if repo_hint:
        candidate = SYSTEM_REPOS_DIR / repo_hint / category / package
        if candidate.is_dir():
            return candidate
        log(f"Package not found in repo '{repo_hint}': {candidate}", "WARN")

    # Search all repos (gentoo first, then others)
    search_order = ["gentoo"]
    for d in sorted(SYSTEM_REPOS_DIR.iterdir()):
        if (
            d.name not in search_order
            and d.name != "gentoo-ai-update-repo"
            and d.is_dir()
        ):
            search_order.append(d.name)

    for repo_name in search_order:
        candidate = SYSTEM_REPOS_DIR / repo_name / category / package
        if candidate.is_dir():
            log(f"Found source package: {candidate}")
            return candidate
    return None


def get_ebuilds(pkg_dir: Path) -> list[Path]:
    """Return sorted list of ebuild files (excluding 9999)."""
    ebuilds = sorted(
        [p for p in pkg_dir.glob("*.ebuild") if "-9999" not in p.stem],
        key=lambda p: p.stem,
    )
    return ebuilds


def extract_version_from_ebuild(ebuild_path: Path, pkg_name: str) -> str:
    """Extract version from ebuild filename: package-VERSION.ebuild → VERSION."""
    stem = ebuild_path.stem  # e.g. "neovim-0.11.5" or "neovim-0.11.3-r1"
    if stem.startswith(pkg_name + "-"):
        return stem[len(pkg_name) + 1 :]
    return stem


def get_latest_version_from_ebuilds(pkg_dir: Path, pkg_name: str) -> str | None:
    """Get the highest version from existing ebuilds."""
    ebuilds = get_ebuilds(pkg_dir)
    if not ebuilds:
        return None
    return extract_version_from_ebuild(ebuilds[-1], pkg_name)


def version_exists(pkg_dir: Path, pkg_name: str, version: str) -> bool:
    """Check if an ebuild for this version already exists."""
    # Check exact version and any revision
    for eb in pkg_dir.glob(f"{pkg_name}-{version}*.ebuild"):
        v = extract_version_from_ebuild(eb, pkg_name)
        # Match base version (ignoring -rN suffix)
        base_v = re.sub(r"-r\d+$", "", v)
        if base_v == version:
            return True
    return False


# ─── Package Analysis ─────────────────────────────────────────────────────────


def extract_ebuild_info(ebuild_path: Path) -> dict:
    """Extract key info from an ebuild file for CLAUDE.md generation."""
    content = ebuild_path.read_text()
    info = {
        "homepage": "",
        "src_uri": "",
        "inherit": "",
        "description": "",
        "slot": "0",
        "iuse": "",
        "license": "",
    }

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("HOMEPAGE="):
            info["homepage"] = line.split("=", 1)[1].strip('"').strip("'")
        elif line.startswith("SRC_URI="):
            info["src_uri"] = line.split("=", 1)[1].strip('"').strip("'")
        elif line.startswith("inherit "):
            info["inherit"] = line[len("inherit ") :]
        elif line.startswith("DESCRIPTION="):
            info["description"] = line.split("=", 1)[1].strip('"').strip("'")
        elif line.startswith("SLOT="):
            info["slot"] = line.split("=", 1)[1].strip('"').strip("'")
        elif line.startswith("IUSE="):
            info["iuse"] = line.split("=", 1)[1].strip('"').strip("'")
        elif line.startswith("LICENSE="):
            info["license"] = line.split("=", 1)[1].strip('"').strip("'")

    # Multi-line SRC_URI — grab the whole block
    if not info["src_uri"]:
        in_src_uri = False
        src_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("SRC_URI="):
                in_src_uri = True
                src_lines.append(stripped.split("=", 1)[1].strip('"').strip("'"))
                if not stripped.endswith('"'):
                    continue
                else:
                    in_src_uri = False
            elif in_src_uri:
                src_lines.append(stripped.rstrip('"').rstrip("'"))
                if stripped.endswith('"') or stripped.endswith("'"):
                    in_src_uri = False
        info["src_uri"] = " ".join(src_lines).strip()

    return info


def extract_remote_id(metadata_path: Path) -> dict:
    """Extract upstream remote-id from metadata.xml."""
    result = {"type": "", "value": ""}
    if not metadata_path.exists():
        return result
    try:
        tree = ET.parse(metadata_path)
        root = tree.getroot()
        for upstream in root.findall("upstream"):
            for remote in upstream.findall("remote-id"):
                result["type"] = remote.get("type", "")
                result["value"] = remote.text or ""
                return result  # Return first one
    except ET.ParseError:
        log(f"Failed to parse {metadata_path}", "WARN")
    return result


def generate_package_claude_md(
    pkg_dir: Path, category: str, package: str, ebuild_info: dict, remote_id: dict
) -> None:
    """Generate package-level CLAUDE.md."""
    content = f"""# {category}/{package}

## Package Info
- **Description**: {ebuild_info["description"]}
- **Homepage**: {ebuild_info["homepage"]}
- **License**: {ebuild_info["license"]}
- **Slot**: {ebuild_info["slot"]}
- **IUSE**: {ebuild_info["iuse"]}

## Source
- **SRC_URI pattern**: `{ebuild_info["src_uri"]}`
- **Eclasses**: `{ebuild_info["inherit"]}`

## Upstream
- **Remote-ID type**: {remote_id["type"]}
- **Remote-ID value**: {remote_id["value"]}
"""

    # Add type-specific hints
    if remote_id["type"] == "github":
        owner, repo = (remote_id["value"].split("/", 1) + [""])[:2]
        content += f"""
## GitHub API
- Releases: `https://api.github.com/repos/{owner}/{repo}/releases/latest`
- Tags: `https://api.github.com/repos/{owner}/{repo}/tags`
"""
    elif remote_id["type"] == "pypi":
        content += f"""
## PyPI API
- JSON: `https://pypi.org/pypi/{remote_id["value"]}/json`
"""
    elif remote_id["type"] == "crates-io":
        content += f"""
## Crates.io API
- JSON: `https://crates.io/api/v1/crates/{remote_id["value"]}`
"""

    content += """
## Notes
- Read the existing ebuild carefully before making changes
- Check `files/` directory for patches that may need updating
- Run `ebuild *.ebuild manifest` after creating new ebuild
- Run `pkgcheck scan` for QA check
"""

    (pkg_dir / "CLAUDE.md").write_text(content)
    log(f"Generated {pkg_dir}/CLAUDE.md")


# ─── Core Actions ─────────────────────────────────────────────────────────────


def setup_package(category: str, package: str, repo_hint: str | None) -> Path:
    """Ensure package exists in our overlay. Copy from source if needed."""
    our_pkg_dir = REPO_DIR / category / package

    if our_pkg_dir.is_dir() and list(our_pkg_dir.glob("*.ebuild")):
        log(f"Package already in overlay: {our_pkg_dir}")
        return our_pkg_dir

    # Find in system repos
    source_dir = find_source_package(category, package, repo_hint)
    if not source_dir:
        log(f"Package {category}/{package} not found in any system repo", "ERR")
        sys.exit(1)

    # Copy to our overlay
    log(f"Copying {source_dir} → {our_pkg_dir}")
    our_pkg_dir.mkdir(parents=True, exist_ok=True)

    # Copy ebuilds, metadata.xml, Manifest, files/
    for item in source_dir.iterdir():
        if item.name in (".git", "__pycache__"):
            continue
        dest = our_pkg_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # Generate package CLAUDE.md
    ebuilds = get_ebuilds(our_pkg_dir)
    if ebuilds:
        ebuild_info = extract_ebuild_info(ebuilds[-1])
        remote_id = extract_remote_id(our_pkg_dir / "metadata.xml")
        generate_package_claude_md(
            our_pkg_dir, category, package, ebuild_info, remote_id
        )
    else:
        log("No ebuilds found after copy — something is wrong", "ERR")
        sys.exit(1)

    return our_pkg_dir


def ensure_get_latest_version_script(
    pkg_dir: Path, category: str, package: str
) -> Path:
    """Ensure get_latest_version.py exists. Create via AI if missing."""
    script_path = pkg_dir / "get_latest_version.py"

    if script_path.exists():
        log(f"get_latest_version.py already exists")
        return script_path

    # Ask AI to create it
    log("Invoking AI to create get_latest_version.py ...", "AI")

    prompt = textwrap.dedent(f"""\
        Create a file called `get_latest_version.py` in the current directory.

        Requirements:
        - Output EXACTLY one line to stdout: the latest stable version number
        - No 'v' prefix (e.g. '0.11.5' not 'v0.11.5')
        - Skip pre-releases, RCs, betas, alphas
        - Exit code 0 on success, non-zero on failure
        - Use Python stdlib only (urllib.request, json, re) — no pip packages
        - If the version cannot be determined, raise an exception with "raise" in the error message
        - Print debug info to stderr only
        - SECURITY: NEVER hardcode any tokens, API keys, or credentials in the script.
          If authentication is needed (e.g. GitHub token for rate limits), read from
          environment variable: os.environ.get("GITHUB_TOKEN"). The token itself must
          NEVER appear in source code, comments, or output.

        Package: {category}/{package}
        Read the CLAUDE.md in this directory for package-specific API info.

        After writing the script, TEST IT by running: python3 get_latest_version.py
        If it fails, fix it until it works.
    """)

    result = run_ai(prompt, cwd=str(pkg_dir))
    if result.returncode != 0:
        log(f"AI failed to create get_latest_version.py: {result.stderr}", "ERR")
        sys.exit(1)

    if not script_path.exists():
        log("AI did not create get_latest_version.py — check AI output above", "ERR")
        log(f"AI stdout: {result.stdout[:500]}", "ERR")
        sys.exit(1)

    log(f"get_latest_version.py created", "OK")
    return script_path


def run_get_latest_version(
    script_path: Path, pkg_dir: Path, category: str, package: str
) -> str | None:
    """
    Run get_latest_version.py with retry logic.
    Returns version string on success, None on failure.
    """
    for attempt in range(1, MAX_VERSION_RETRIES + 1):
        log(f"Running get_latest_version.py (attempt {attempt}/{MAX_VERSION_RETRIES})")
        result = run_cmd(["python3", str(script_path)], cwd=str(pkg_dir))

        if result.returncode == 0:
            version = result.stdout.strip()
            if version and re.match(r"^[0-9]", version):
                log(f"Got version: {version}", "OK")
                return version
            else:
                log(f"Invalid version output: '{version}'", "WARN")
        else:
            stderr = result.stderr.strip()
            log(
                f"get_latest_version.py failed (exit {result.returncode}): {stderr}",
                "WARN",
            )

            # Check if "raise" is in the error — means method is wrong, try web search
            if "raise" in stderr.lower() or "raise" in result.stdout.lower():
                log(
                    "Script raised — version method is wrong. Trying AI web search fallback.",
                    "WARN",
                )
                return _ai_web_search_version(pkg_dir, category, package)

    # All retries failed — ask AI to fix the script
    log("All retries failed. Asking AI to fix get_latest_version.py ...", "AI")
    last_error = result.stderr.strip() if result else "Unknown error"  # type: ignore[possibly-unbound]

    fix_prompt = textwrap.dedent(f"""\
        The file `get_latest_version.py` in this directory is failing.
        Last error: {last_error}

        Please fix the script so it correctly outputs the latest stable version
        of {category}/{package} to stdout (one line, no 'v' prefix).

        Read CLAUDE.md for package info. Test the fix by running: python3 get_latest_version.py
    """)

    fix_result = run_ai(fix_prompt, cwd=str(pkg_dir))

    # Retry once after fix
    result = run_cmd(["python3", str(script_path)], cwd=str(pkg_dir))
    if result.returncode == 0:
        version = result.stdout.strip()
        if version and re.match(r"^[0-9]", version):
            log(f"Got version after fix: {version}", "OK")
            return version

    log("Still failing after AI fix. Preserving scene for manual investigation.", "ERR")
    log(f"Package dir: {pkg_dir}", "ERR")
    log(f"Last stdout: {result.stdout.strip()}", "ERR")
    log(f"Last stderr: {result.stderr.strip()}", "ERR")
    return None


def _ai_web_search_version(pkg_dir: Path, category: str, package: str) -> str | None:
    """Use AI agent to search the web for latest version."""
    log("Using AI to search web/other distros for latest version...", "AI")

    prompt = textwrap.dedent(f"""\
        I need to find the latest stable release version of {category}/{package}.
        The automated script couldn't determine it.

        Please search the web (upstream project page, GitHub, distro packages, repology.org, etc.)
        to find the latest stable version.

        Read CLAUDE.md in this directory for upstream info.

        After finding the version, update `get_latest_version.py` to correctly fetch it,
        then TEST the script by running: python3 get_latest_version.py

        The script must output exactly one line: the version number (no 'v' prefix).
    """)

    result = run_ai(prompt, cwd=str(pkg_dir))

    # Try running the (presumably fixed) script
    script_path = pkg_dir / "get_latest_version.py"
    if script_path.exists():
        run_result = run_cmd(["python3", str(script_path)], cwd=str(pkg_dir))
        if run_result.returncode == 0:
            version = run_result.stdout.strip()
            if version and re.match(r"^[0-9]", version):
                log(f"Got version via web search fallback: {version}", "OK")
                return version

    log("Web search fallback also failed.", "ERR")
    return None


def update_ebuild(pkg_dir: Path, category: str, package: str, new_version: str) -> bool:
    """Ask AI to create new version ebuild, generate manifest, run pkgcheck."""
    log(f"Updating ebuild to version {new_version} ...", "AI")

    ebuilds = get_ebuilds(pkg_dir)
    if not ebuilds:
        log("No existing ebuilds to base update on", "ERR")
        return False

    latest_ebuild = ebuilds[-1]
    old_version = extract_version_from_ebuild(latest_ebuild, package)

    prompt = textwrap.dedent(f"""\
        Update {category}/{package} from version {old_version} to {new_version}.

        Steps:
        1. Copy {latest_ebuild.name} to {package}-{new_version}.ebuild
        2. Review the new ebuild — usually no changes needed for simple version bumps.
           But check if:
           - Patches in files/ reference the old version
           - SRC_URI pattern needs adjustment
           - Dependencies have changed upstream
        3. Generate Manifest:
           Run: ebuild {package}-{new_version}.ebuild manifest
        4. Run: pkgcheck scan
           Fix any errors. Warnings are OK.

        Read CLAUDE.md for package-specific info.
        Do NOT modify or remove old ebuilds.
        Do NOT commit anything.
    """)

    result = run_ai(prompt, cwd=str(pkg_dir), model=AI_MODEL_CODE)

    # Verify the new ebuild was created
    new_ebuild = pkg_dir / f"{package}-{new_version}.ebuild"
    if not new_ebuild.exists():
        log(f"New ebuild {new_ebuild.name} was not created", "ERR")
        log(f"AI stdout: {result.stdout[:500]}", "ERR")
        return False

    # Verify Manifest was updated
    manifest = pkg_dir / "Manifest"
    if not manifest.exists():
        log("Manifest not found — trying to generate...", "WARN")
        run_cmd(["ebuild", str(new_ebuild), "manifest"], cwd=str(pkg_dir))

    # Final pkgcheck
    log("Running final pkgcheck scan...")
    pkgcheck_result = run_cmd(["pkgcheck", "scan"], cwd=str(pkg_dir))
    if pkgcheck_result.stdout:
        log(f"pkgcheck output:\n{pkgcheck_result.stdout}", "WARN")

    log(f"Ebuild {new_ebuild.name} created successfully", "OK")
    return True


def ensure_test_script(pkg_dir: Path, category: str, package: str) -> Path | None:
    """Ensure test_ebuild.py exists. Create via AI if missing."""
    script_path = pkg_dir / "test_ebuild.py"

    if script_path.exists():
        log("test_ebuild.py already exists")
        return script_path

    log("Invoking AI to create test_ebuild.py ...", "AI")

    # Build the podman test command the AI can use to validate its script
    gentoo_repo = SYSTEM_REPOS_DIR / "gentoo"
    test_version = get_latest_version_from_ebuilds(pkg_dir, package) or "VERSION"
    podman_test_cmd = (
        f"podman run --rm --privileged"
        f" -v {gentoo_repo}:/var/db/repos/gentoo:ro"
        f" -v {REPO_DIR}:/var/db/repos/gentoo-ai-update-repo"
        f" {CONTAINER_IMAGE} /bin/bash -c '"
        f"mkdir -p /etc/portage/repos.conf && "
        f'echo "[DEFAULT]\nmain-repo = gentoo\n[gentoo]\nlocation = /var/db/repos/gentoo" > /etc/portage/repos.conf/gentoo.conf && '
        f'echo "[gentoo-ai-update-repo]\nlocation = /var/db/repos/gentoo-ai-update-repo\nmasters = gentoo" > /etc/portage/repos.conf/ai-overlay.conf && '
        f'echo "={category}/{package}-{test_version} **" > /etc/portage/package.accept_keywords/ai-test && '
        f"emerge -1v ={category}/{package}-{test_version} && "
        f"python3 /var/db/repos/gentoo-ai-update-repo/{category}/{package}/test_ebuild.py {test_version}"
        f"'"
    )

    prompt = textwrap.dedent(f"""\
        Create a file called `test_ebuild.py` in the current directory.

        This is a black-box smoke test for {category}/{package}.
        It runs inside a Gentoo stage3 container after the package is emerged.
        Usage: python3 test_ebuild.py VERSION

        Write tests that verify the package actually works. Use your judgement based
        on what this package does. At minimum:
        1. Version check: verify VERSION string appears in program output
        2. Core functionality: exercise the program's main feature with real input
        3. Installed files: check key files exist (binary, man page, etc.)
        Add more tests if obvious and cheap, but keep it simple.

        Technical requirements:
        - Accept VERSION as first CLI argument
        - Python stdlib only — no pip packages
        - Exit 0 if all pass, non-zero on any failure
        - Print each test: [PASS] or [FAIL] with name

        Read CLAUDE.md for package info.

        IMPORTANT: After writing test_ebuild.py, you MUST validate it yourself by running:

        {podman_test_cmd}

        This runs the full flow: emerge the package in a container, then run your test.
        If any tests fail, analyze the output, fix the script, and re-run until all tests pass.
        The overlay is mounted read-write so your edits take effect immediately.
        Do not finish until the test passes in the container.
    """)

    result = run_ai(prompt, cwd=str(pkg_dir), model=AI_MODEL_CODE)

    if script_path.exists():
        log("test_ebuild.py created", "OK")
        return script_path
    else:
        log("AI did not create test_ebuild.py — skipping container test", "WARN")
        return None


def run_container_test(
    pkg_dir: Path, category: str, package: str, version: str
) -> bool:
    """Run test_ebuild.py inside a Gentoo stage3 container."""
    test_script = pkg_dir / "test_ebuild.py"
    if not test_script.exists():
        log("No test_ebuild.py — skipping container test", "WARN")
        return True  # Don't block on missing test

    log(f"Running container test for {category}/{package}-{version} ...")

    # Check if container image exists, pull if needed
    check = run_cmd(["podman", "image", "exists", CONTAINER_IMAGE])
    if check.returncode != 0:
        log(f"Pulling {CONTAINER_IMAGE} (first time) ...", "AI")
        pull = run_cmd(["podman", "pull", CONTAINER_IMAGE], capture=False)
        if pull.returncode != 0:
            log("Failed to pull container image", "ERR")
            return False

    # Run container with host repos mounted
    # The stage3 image has a profile symlink to /var/db/repos/gentoo/profiles/...
    # but no actual gentoo repo inside. Mount the host's repos to provide it.
    gentoo_repo = SYSTEM_REPOS_DIR / "gentoo"
    container_cmd = [
        "podman",
        "run",
        "--rm",
        "--privileged",
        "-v",
        f"{gentoo_repo}:/var/db/repos/gentoo:ro",
        "-v",
        f"{REPO_DIR}:/var/db/repos/gentoo-ai-update-repo:ro",
        CONTAINER_IMAGE,
        "/bin/bash",
        "-c",
        f"""
set -e

# Configure repos
mkdir -p /etc/portage/repos.conf
cat > /etc/portage/repos.conf/gentoo.conf << 'REPOEOF'
[DEFAULT]
main-repo = gentoo

[gentoo]
location = /var/db/repos/gentoo
REPOEOF

cat > /etc/portage/repos.conf/ai-overlay.conf << 'REPOEOF'
[gentoo-ai-update-repo]
location = /var/db/repos/gentoo-ai-update-repo
masters = gentoo
REPOEOF

# Accept testing keywords for this package
echo "={category}/{package}-{version} **" > /etc/portage/package.accept_keywords/ai-test

# Emerge the package
emerge -1v ={category}/{package}-{version}

# Run smoke test
python3 /var/db/repos/gentoo-ai-update-repo/{category}/{package}/test_ebuild.py {version}
        """,
    ]

    result = run_cmd(container_cmd, capture=False)

    if result.returncode == 0:
        log(f"Container test PASSED", "OK")
        return True
    else:
        log(f"Container test FAILED (exit {result.returncode})", "ERR")
        return False


def print_summary(
    category: str, package: str, version: str, pkg_dir: Path, test_passed: bool
):
    """Print final summary with git suggestions."""
    print()
    print("=" * 60)
    print(f"  Update Summary: {category}/{package}")
    print("=" * 60)
    print(f"  New version : {version}")
    print(f"  Package dir : {pkg_dir}")
    print(f"  Container   : {'PASSED' if test_passed else 'FAILED / SKIPPED'}")
    print()
    print("  Suggested git commands:")
    print(f"    cd {pkg_dir}")
    print(f"    git add -A")
    print(f'    git commit -m "bump {category}/{package} to {version}"')
    print("=" * 60)
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="AI-driven Gentoo ebuild updater",
        epilog="Example: python3 update.py app-editors/neovim",
    )
    parser.add_argument(
        "package", help="Package atom: category/package or category/package::repo"
    )
    parser.add_argument("--skip-test", action="store_true", help="Skip container test")
    parser.add_argument(
        "--force", action="store_true", help="Force update even if version exists"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only check version, don't update"
    )
    args = parser.parse_args()

    category, package, repo_hint = parse_package_atom(args.package)
    log(
        f"Processing {category}/{package}"
        + (f" (hint: {repo_hint})" if repo_hint else "")
    )

    # Step 1: Ensure package is in our overlay
    pkg_dir = setup_package(category, package, repo_hint)

    # Step 2: Ensure get_latest_version.py exists
    script_path = ensure_get_latest_version_script(pkg_dir, category, package)

    # Step 3: Get latest version
    new_version = run_get_latest_version(script_path, pkg_dir, category, package)
    if new_version is None:
        log("Could not determine latest version. Exiting.", "ERR")
        sys.exit(1)

    # Step 4: Check if we already have this version
    if not args.force and version_exists(pkg_dir, package, new_version):
        current = get_latest_version_from_ebuilds(pkg_dir, package)
        log(
            f"Already up to date: {category}/{package}-{current} (upstream: {new_version})",
            "OK",
        )
        sys.exit(0)

    if args.dry_run:
        current = get_latest_version_from_ebuilds(pkg_dir, package)
        log(f"Update available: {current} → {new_version}", "OK")
        sys.exit(0)

    # Step 5: Update ebuild
    success = update_ebuild(pkg_dir, category, package, new_version)
    if not success:
        log("Ebuild update failed. Preserving scene for investigation.", "ERR")
        sys.exit(1)

    # Step 6: Container test (optional)
    test_passed = True
    if not args.skip_test:
        ensure_test_script(pkg_dir, category, package)
        test_passed = run_container_test(pkg_dir, category, package, new_version)
    else:
        log("Container test skipped (--skip-test)", "WARN")

    # Step 7: Summary
    print_summary(category, package, new_version, pkg_dir, test_passed)


if __name__ == "__main__":
    main()
