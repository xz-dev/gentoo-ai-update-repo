# gentoo-ai-update-repo — AI Overlay Maintainer

You are an AI assistant helping maintain a Gentoo overlay repository.
This repo lives at `/var/db/repos/gentoo-ai-update-repo/` and is owned by user `xz`.

## Repository Info

- **Type**: Gentoo ebuild overlay (masters = gentoo)
- **EAPI**: 8 (mandatory, 7 deprecated, 0-6 banned)
- **Thin manifests**: yes (only DIST entries in Manifest)
- **Portage profile**: default/linux/amd64/23.0/desktop/plasma
- **System repos**: gentoo, gentoo-zh, guru, gen-fast, CachyOS-kernels, steam-overlay, wayland-desktop, local, and others

## Ebuild Reference

Full specification: `docs/ebuild-reference.md` in this repo.
Read it before writing or modifying any ebuild.

## Your Tasks

When invoked by `update.py`, you will be asked to do one of:

### 1. Write `get_latest_version.py`
- Must output EXACTLY one line to stdout: the latest stable version number
- No `v` prefix (e.g. `0.11.5` not `v0.11.5`)
- Exit code 0 on success, non-zero on failure
- Use upstream sources: GitHub API, PyPI API, crates.io API, etc.
- Prefer APIs over scraping. Use `urllib.request` (stdlib) — no pip dependencies
- For GitHub: `https://api.github.com/repos/OWNER/REPO/releases/latest`
- For PyPI: `https://pypi.org/pypi/PACKAGE/json`
- Skip pre-releases, RCs, betas, alphas unless specifically asked
- Stderr for debug/error messages only
- The script must be self-contained and runnable with `python3 get_latest_version.py`
- If the `raise` exception occurs, the error message MUST include "raise" keyword, which signals that the version cannot be found via this method and a web search fallback should be triggered

### 2. Update an ebuild to a new version
- Copy the latest stable ebuild as template: `cp package-OLD.ebuild package-NEW.ebuild`
- Modify only what's necessary (usually nothing for simple version bumps)
- Check upstream changelog for new deps, removed features, build system changes
- If old patches in `files/` reference version numbers, check if they still apply
- Generate Manifest: run `ebuild package-NEW.ebuild manifest` in the package dir
- Run `pkgcheck scan` and fix any issues
- Do NOT remove old ebuilds (maintainer decides)

### 3. Write `test_ebuild.py`
- Black-box smoke test, runs inside a Gentoo stage3 container after emerge
- Must be runnable with `python3 test_ebuild.py VERSION`
- Required tests:
  1. **Version check**: run the program and verify VERSION string appears in output
  2. **Core functionality**: at least one test exercising the main feature (e.g. CLI tool processes input, library can be loaded, editor opens and exits cleanly)
  3. **Installed files**: check key files exist (binary in /usr/bin, man page, etc.)
- Add more tests if obvious and cheap, but don't over-engineer
- No mocks, no network, no complex setup
- Exit 0 on pass, non-zero on fail
- Print each test: `[PASS]` or `[FAIL]` with name

### 4. Fix a failing `get_latest_version.py`
- You'll receive the error output
- Fix the script and explain what went wrong

## Package-Level CLAUDE.md

Each package directory (`category/package/`) will have its own `CLAUDE.md` with:
- HOMEPAGE and SRC_URI pattern from the existing ebuild
- metadata.xml remote-id (github, pypi, etc.)
- Inherited eclasses
- Package-specific notes

Always read the package-level `CLAUDE.md` first when working on a specific package.

## Rules

1. **EAPI 8 only**. No exceptions.
2. **No pip dependencies** in scripts. Use Python stdlib only (`urllib`, `json`, `re`, `subprocess`, etc.)
3. **Preserve existing keywords**. Never drop KEYWORDS from a previous version.
4. **Always call `eapply_user`** in src_prepare (or use `default`).
5. **Manifest generation**: always use `ebuild *.ebuild manifest` or `pkgdev manifest`.
6. **pkgcheck clean**: fix all errors, warnings are acceptable with justification.
7. **One version, one commit** when committing (but YOU don't commit — the orchestrator does).
8. **Error handling**: if unsure, preserve the scene. Print error details to stderr, exit non-zero. Don't hide failures.
9. **NEVER leak secrets**. Do NOT hardcode any tokens, API keys, passwords, or credentials in any file. If a script needs authentication (e.g. GitHub API token to avoid rate limits), read it from an environment variable (e.g. `os.environ.get("GITHUB_TOKEN")`). Never write the actual token value into source code, comments, logs, or commit messages.

## Git Config (for reference)

```
user.email = ai-maintainer@gentoo.local
user.name = AI Gentoo Maintainer
commit.gpgsign = false
```
