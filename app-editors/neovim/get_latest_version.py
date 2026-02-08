#!/usr/bin/env python3
"""Get the latest stable version of Neovim from GitHub releases."""

import json
import re
import sys
import urllib.request


def get_latest_version():
    """Fetch latest stable version from GitHub API."""
    url = "https://api.github.com/repos/neovim/neovim/releases/latest"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        tag_name = data.get("tag_name", "")

        if not tag_name:
            raise ValueError("raise: No tag_name found in GitHub response")

        # Remove 'v' prefix if present
        version = tag_name.lstrip("v")

        # Skip pre-releases, RCs, betas, alphas
        # Check if this is a pre-release according to GitHub
        if data.get("prerelease", False):
            print(
                f"Warning: Version {version} is marked as pre-release", file=sys.stderr
            )

        # Also check version string for common pre-release patterns
        pre_release_patterns = [
            r"-alpha",
            r"-beta",
            r"-rc",
            r"-RC",
            r"rc",
            r"RC",
            r"alpha",
            r"beta",
            r"-dev",
            r"\.dev",
            r"-pre",
        ]

        for pattern in pre_release_patterns:
            if re.search(pattern, version):
                raise ValueError(
                    f"raise: Version {version} appears to be a pre-release (matches {pattern})"
                )

        # Validate version looks like a semantic version
        if not re.match(r"^\d+(\.\d+)*$", version):
            raise ValueError(
                f"raise: Version {version} doesn't look like a valid stable version"
            )

        return version

    except urllib.error.HTTPError as e:
        raise ValueError(f"raise: HTTP error {e.code} when fetching {url}: {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"raise: URL error when fetching {url}: {e.reason}")
    except json.JSONDecodeError as e:
        raise ValueError(f"raise: JSON decode error: {e}")


def main():
    """Main entry point."""
    try:
        version = get_latest_version()
        print(version)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
