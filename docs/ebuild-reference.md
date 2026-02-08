# Ebuild Quick Reference for AI Agents

> Compressed EAPI 8 specification. For full details: devmanual.gentoo.org

## 1. File Structure

```
category/package/
├── package-1.0.ebuild      # Version-specific ebuild
├── package-1.1.ebuild
├── package-9999.ebuild      # Live/git ebuild (optional)
├── Manifest                 # Distfile checksums
├── metadata.xml             # Package metadata (maintainer, USE flags, upstream)
└── files/                   # Patches and other files
    └── package-1.0-fix.patch
```

## 2. Ebuild Template (EAPI 8)

```bash
# Copyright 2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

EAPI=8

# Eclasses must be inherited BEFORE using their functions/variables
inherit cmake    # or meson, cargo, go-module, distutils-r1, etc.

DESCRIPTION="Short description (max ~80 chars)"
HOMEPAGE="https://example.com"
SRC_URI="https://github.com/foo/bar/archive/v${PV}.tar.gz -> ${P}.tar.gz"

# For GitHub releases:
# SRC_URI="https://github.com/${PN}/${PN}/archive/refs/tags/v${PV}.tar.gz -> ${P}.tar.gz"
# For PyPI:
# SRC_URI="https://files.pythonhosted.org/packages/source/${PN::1}/${PN}/${P}.tar.gz"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~arm64"
IUSE="test doc"
RESTRICT="!test? ( test )"

# Dependencies
RDEPEND="
	>=dev-libs/libfoo-1.0:=
	dev-libs/bar
"
DEPEND="${RDEPEND}
	test? ( dev-util/test-framework )
"
BDEPEND="
	virtual/pkgconfig
	doc? ( app-text/doxygen )
"

src_configure() {
	local mycmakeargs=(
		-DENABLE_TEST=$(usex test)
		-DENABLE_DOC=$(usex doc)
	)
	cmake_src_configure
}
```

## 3. Key Variables

### Predefined (read-only)
| Variable | Example for `app-editors/neovim-0.11.5-r1` |
|----------|----------------------------------------------|
| P        | neovim-0.11.5                                |
| PN       | neovim                                       |
| PV       | 0.11.5                                       |
| PR       | r1                                           |
| PVR      | 0.11.5-r1                                    |
| PF       | neovim-0.11.5-r1                             |
| CATEGORY | app-editors                                  |
| FILESDIR | ${portage_builddir}/files (= files/ in repo) |
| WORKDIR  | ${portage_builddir}/work                     |
| S        | ${WORKDIR}/${P} (default)                    |
| D        | ${portage_builddir}/image                    |
| ED       | ${D%/}/ (with EPREFIX)                       |

### Must-set
| Variable    | Description |
|-------------|-------------|
| EAPI        | Must be `8` |
| DESCRIPTION | ≤80 chars, no trailing period |
| HOMEPAGE    | Upstream URL(s), space-separated |
| SRC_URI     | Download URL(s) with optional rename `-> filename` |
| LICENSE     | SPDX-style, e.g. `MIT`, `GPL-2+`, `Apache-2.0` |
| SLOT        | Usually `0` unless multiple versions coexist |
| KEYWORDS    | `~amd64` for testing, `amd64` for stable |

### Optional
| Variable | Description |
|----------|-------------|
| IUSE     | USE flags this ebuild checks |
| RESTRICT | `mirror`, `test`, `fetch`, `bindist`, `strip` |
| RDEPEND  | Runtime deps |
| DEPEND   | Build+runtime deps (headers, etc.) |
| BDEPEND  | Build-only deps (tools, compilers) - EAPI 7+ |
| IDEPEND  | Install-time deps (post-merge tools) - EAPI 8 only |
| PDEPEND  | Post-merge deps (for circular deps) |
| PATCHES  | Array of patches applied in src_prepare |

## 4. Dependency Syntax

```bash
# Version operators
>=category/package-1.0       # >= 1.0
<=category/package-2.0       # <= 2.0
=category/package-1.0*       # 1.0.x (any 1.0.*)
~category/package-1.0        # any revision of 1.0 (1.0, 1.0-r1, ...)
!category/package             # blocker (conflict)
!!category/package            # hard blocker

# SLOT deps
dev-libs/foo:2               # exactly slot 2
dev-libs/foo:=               # slot operator - rebuild when slot changes
dev-libs/foo:2=              # slot 2, rebuild if subslot changes
dev-libs/foo:*               # any slot

# USE deps
dev-libs/foo[bar]            # foo must have USE=bar enabled
dev-libs/foo[bar,baz]        # both bar and baz
dev-libs/foo[-bar]           # bar must be disabled
dev-libs/foo[bar?]           # if this package has USE=bar, foo needs it too
dev-libs/foo[bar=]           # foo's bar must match this package's bar

# Conditional
ssl? ( dev-libs/openssl )
!libressl? ( dev-libs/openssl )
```

## 5. Phase Functions

Execution order:

```
pkg_pretend → pkg_setup → src_unpack → src_prepare → src_configure
→ src_compile → src_test → src_install → pkg_preinst → pkg_postinst
→ pkg_prerm → pkg_postrm
```

### Common overrides:
- `src_prepare`: Apply patches (always call `default` or `eapply_user`)
- `src_configure`: Set build options
- `src_compile`: Build (most eclasses handle this)
- `src_install`: Install files
- `src_test`: Run tests (conditional on USE=test + RESTRICT)

### Helper functions:
```bash
# Installation
dobin, dosbin, dolib.so, dolib.a    # Install to standard paths
doman, dodoc, doinfo, dohtml        # Docs
doins, doexe, dodir, dosym          # Generic
keepdir                              # Empty directory placeholder
insinto /usr/share/${PN}; doins file # Install to custom path
newbin oldname newname               # Rename during install

# Patches
eapply "${FILESDIR}/fix.patch"       # Apply one patch
eapply_user                          # Apply user patches (REQUIRED in src_prepare)
PATCHES=( "${FILESDIR}/${P}-fix.patch" )  # Auto-applied by default src_prepare

# USE flags
use flag       # Returns 0 if flag enabled
usex flag yes no  # Echo "yes" or "no"

# Output
elog "message"  # Informational (shown post-merge)
ewarn "message" # Warning
eerror "message" # Error (doesn't stop build)
die "message"   # Fatal error, stops build
```

## 6. Common Eclasses Cheatsheet

### cmake
```bash
inherit cmake
# Override: src_configure() { local mycmakeargs=( -DFOO=ON ); cmake_src_configure; }
# Provides: cmake_src_configure, cmake_src_compile, cmake_src_install, cmake_src_test
# Sets BUILD_DIR="${WORKDIR}/${P}_build"
```

### meson
```bash
inherit meson
# Override: src_configure() { local emesonargs=( $(meson_use feat) ); meson_src_configure; }
# Helpers: meson_use, meson_feature (returns enabled/disabled)
```

### cargo (Rust)
```bash
inherit cargo
# SRC_URI += "$(cargo_crate_uris)" or vendor tarball
# ECARGO_VENDOR="${WORKDIR}/vendor"
# QA_FLAGS_IGNORED="usr/bin/.*" (Rust doesn't respect CFLAGS)
```

### go-module (Go)
```bash
inherit go-module
# SRC_URI += vendor tarball: "${P}-deps.tar.xz"
# Or EGO_SUM=( "github.com/foo/bar v1.0.0" ... )
```

### distutils-r1 (Python)
```bash
inherit distutils-r1
DISTUTILS_USE_PEP517=setuptools  # or poetry, flit, hatchling, maturin, etc.
PYTHON_COMPAT=( python3_{11..13} )
# Phases: python_configure, python_compile, python_test, python_install
```

### git-r3 (live ebuilds)
```bash
inherit git-r3
EGIT_REPO_URI="https://github.com/foo/bar.git"
# No SRC_URI, no KEYWORDS for live ebuilds
```

### xdg (desktop apps)
```bash
inherit xdg
# Auto-updates icon cache, desktop database, mime database in pkg_postinst/pkg_postrm
```

## 7. SRC_URI Patterns

```bash
# GitHub release tarball
SRC_URI="https://github.com/OWNER/REPO/archive/v${PV}.tar.gz -> ${P}.tar.gz"
# or release asset:
SRC_URI="https://github.com/OWNER/REPO/releases/download/v${PV}/${P}.tar.gz"

# GitLab
SRC_URI="https://gitlab.com/OWNER/REPO/-/archive/v${PV}/${PN}-v${PV}.tar.gz -> ${P}.tar.gz"

# PyPI
SRC_URI="https://files.pythonhosted.org/packages/source/${PN::1}/${PN}/${P}.tar.gz"
# or with PYPI_NO_NORMALIZE: inherit pypi

# crates.io (usually via cargo eclass)
# Codeberg
SRC_URI="https://codeberg.org/OWNER/REPO/archive/v${PV}.tar.gz -> ${P}.tar.gz"

# S adjustment (when tarball extracts to different name)
S="${WORKDIR}/${PN}-v${PV}"     # if tarball has v prefix
S="${WORKDIR}/repo-${PV}"       # if upstream uses different name
```

## 8. Manifest

Format: `DIST <filename> <size> BLAKE2B <hash> SHA512 <hash>`

Generate with:
```bash
# In the package directory:
ebuild package-1.0.ebuild manifest
# or:
pkgdev manifest
```

For thin-manifests (our overlay): only DIST entries, no checksums for ebuilds/files.

## 9. metadata.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE pkgmetadata SYSTEM "https://www.gentoo.org/dtd/metadata.dtd">
<pkgmetadata>
  <maintainer type="person">
    <email>ai-maintainer@gentoo.local</email>
    <name>AI Gentoo Maintainer</name>
  </maintainer>
  <upstream>
    <remote-id type="github">owner/repo</remote-id>
    <!-- types: github, gitlab, pypi, crates-io, bitbucket, codeberg,
         freedesktop-gitlab, gnome-gitlab, kde-invent, sourceforge, cpan -->
  </upstream>
  <use>
    <flag name="foo">Enable foo support</flag>
  </use>
</pkgmetadata>
```

## 10. Version Format

Gentoo version: `[0-9]+(\.[0-9]+)*[a-z]?(_alpha|_beta|_pre|_rc|_p[0-9]+)?(-r[0-9]+)?`

Ordering: `_alpha < _beta < _pre < _rc < (no suffix) < _p`

Examples:
- `1.0_alpha` < `1.0_beta` < `1.0_rc1` < `1.0` < `1.0_p1` < `1.0-r1`
- Upstream `1.0-beta2` → Gentoo `1.0_beta2`
- Upstream `1.0.0-rc.1` → Gentoo `1.0.0_rc1`

## 11. pkgcheck Common Fixes

| Issue | Fix |
|-------|-----|
| `MissingSlotDep` | Add `:=` or `:SLOT` to dependency |
| `DeprecatedEapi` | Bump to EAPI 8 |
| `RedundantVersion` | Remove unnecessary `>=cat/pkg-0` |
| `MissingUseDepDefault` | Add `[flag(+)]` or `[flag(-)]` for cross-repo deps |
| `EbuildSemicolon` | Remove trailing semicolons |
| `AbsoluteSymlink` | Use relative symlinks in dosym -r |
| `MissingTestRestrict` | Add `RESTRICT="!test? ( test )"` |
| `VariableScope` | Certain variables only in certain phases |
| `DroppedKeywords` | Don't remove KEYWORDS present in previous version |
| `InvalidCopyright` | Must match `# Copyright YYYY Gentoo Authors` |

## 12. Version Bumping Workflow

1. Copy the latest stable ebuild: `cp package-1.0.ebuild package-1.1.ebuild`
2. Edit the new ebuild if needed (dependency changes, new features, etc.)
3. Generate Manifest: `ebuild package-1.1.ebuild manifest` or `pkgdev manifest`
4. Run QA: `pkgcheck scan`
5. Test: `emerge -1v =category/package-1.1`
6. Commit: one commit per package change

### Common version bump changes:
- Usually NONE needed if upstream is well-behaved (same build system, no API breaks)
- Check upstream CHANGELOG for new deps, removed features, build system changes
- If patches in `files/` exist for old version, check if still needed
- Update `PATCHES` array if patch filenames reference version

## 13. EAPI 8 Specific Features

- `IDEPEND`: Install-time dependencies (tools needed for pkg_postinst, etc.)
- `dosym -r`: Creates relative symlinks automatically
- `econf` passes `--datarootdir`, `--disable-static` by default
- `usev flag [value]`: Like `use` but echoes flag name or value
- Group functions: `eqawarn` for QA warnings
- `install-qa-check.d`: QA check hooks
- Selective fetch/mirror restriction per-file
- `PROPERTIES=live` for non-VCS live packages
