# gentoo-ai-update-repo

AI-driven Gentoo overlay that automates ebuild version bumps.

## How It Works

```
python3 update.py app-editors/neovim
```

`update.py` is a thin orchestrator. It delegates all "smart" work to AI agents via [opencode](https://opencode.ai):

1. **Copy package** from system repos (gentoo, guru, etc.) into this overlay
2. **AI generates `get_latest_version.py`** — a per-package script that queries upstream APIs (GitHub, PyPI, crates.io, etc.) for the latest stable release
3. **Check version** — if upstream is newer, proceed; otherwise exit
4. **AI creates new ebuild** — copies latest ebuild, adjusts if needed, generates Manifest, runs `pkgcheck scan`
5. **Container test** — `podman run gentoo/stage3` with overlay mounted, emerges the package, runs AI-generated smoke tests

Two AI models are used:
- `kimi-k2.5` — version checking, web/API queries
- `minimax-m2.1` — writing ebuilds, test scripts, code

## Usage

```bash
# Check and update a package (full flow with container test)
python3 update.py app-editors/neovim

# Dry run — only check if update is available
python3 update.py app-editors/neovim --dry-run

# Skip container test
python3 update.py app-editors/neovim --skip-test

# Force re-run even if version already exists
python3 update.py app-editors/neovim --force

# Specify source repo
python3 update.py app-editors/neovim::gentoo
```

## Repository Structure

```
.
├── update.py                  # Main orchestrator
├── CLAUDE.md                  # AI agent system instructions
├── docs/
│   └── ebuild-reference.md    # EAPI 8 quick reference for AI
├── metadata/
│   └── layout.conf            # Overlay config (masters = gentoo)
├── profiles/
│   └── repo_name              # "gentoo-ai-update-repo"
└── app-editors/neovim/        # Example: managed package
    ├── CLAUDE.md              # Auto-generated package context for AI
    ├── get_latest_version.py  # AI-generated version checker
    ├── test_ebuild.py         # AI-generated smoke test
    ├── neovim-0.11.6.ebuild   # Bumped ebuild
    ├── Manifest
    ├── metadata.xml
    └── files/                 # Patches
```

Each package directory is self-contained. The AI-generated scripts (`get_latest_version.py`, `test_ebuild.py`) and context (`CLAUDE.md`) are persisted and reused across runs.

## Requirements

- Gentoo Linux with portage
- [opencode](https://opencode.ai) CLI (`opencode run`)
- `pkgcheck`, `pkgdev` (from `dev-util/pkgcheck`, `dev-util/pkgdev`)
- `podman` (for container tests)
- Python 3.11+

## Portage Setup

This repo is already registered in `/etc/portage/repos.conf/`:

```ini
[gentoo-ai-update-repo]
location = /var/db/repos/gentoo-ai-update-repo
sync-type = git
sync-uri = https://codeberg.org/xz-dev/gentoo-ai-update-repo.git
auto-sync = no
```

Packages in this overlay take priority over the main gentoo repo.
