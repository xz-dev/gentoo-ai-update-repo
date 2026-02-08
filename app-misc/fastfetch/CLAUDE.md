# app-misc/fastfetch

## Package Info
- **Description**: Fast neofetch-like system information tool
- **Homepage**: https://github.com/fastfetch-cli/fastfetch
- **License**: MIT
- **Slot**: 0
- **IUSE**: X chafa dbus ddcutil drm elf gnome imagemagick opencl opengl pulseaudio sqlite test vulkan wayland xcb xrandr

## Source
- **SRC_URI pattern**: `https://github.com/fastfetch-cli/fastfetch/archive/refs/tags/${PV}.tar.gz -> ${P}.tar.gz`
- **Eclasses**: `git-r3`

## Upstream
- **Remote-ID type**: github
- **Remote-ID value**: fastfetch-cli/fastfetch

## GitHub API
- Releases: `https://api.github.com/repos/fastfetch-cli/fastfetch/releases/latest`
- Tags: `https://api.github.com/repos/fastfetch-cli/fastfetch/tags`

## Notes
- Read the existing ebuild carefully before making changes
- Check `files/` directory for patches that may need updating
- Run `ebuild *.ebuild manifest` after creating new ebuild
- Run `pkgcheck scan` for QA check
