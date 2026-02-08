# app-editors/neovim

## Package Info
- **Description**: Vim-fork focused on extensibility and agility
- **Homepage**: https://neovim.io
- **License**: Apache-2.0 vim
- **Slot**: 0
- **IUSE**: +nvimpager test

## Source
- **SRC_URI pattern**: `https://github.com/neovim/neovim/archive/v${PV}.tar.gz -> ${P}.tar.gz`
- **Eclasses**: `git-r3`

## Upstream
- **Remote-ID type**: github
- **Remote-ID value**: neovim/neovim

## GitHub API
- Releases: `https://api.github.com/repos/neovim/neovim/releases/latest`
- Tags: `https://api.github.com/repos/neovim/neovim/tags`

## Notes
- Read the existing ebuild carefully before making changes
- Check `files/` directory for patches that may need updating
- Run `ebuild *.ebuild manifest` after creating new ebuild
- Run `pkgcheck scan` for QA check
