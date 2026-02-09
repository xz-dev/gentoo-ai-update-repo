#!/usr/bin/env python3
"""Get the latest stable version of Neovim from GitHub releases."""

import re
import sys
import urllib.error
import urllib.request


def get_latest_version():
    """Fetch latest stable version from GitHub releases page."""
    url = "https://github.com/neovim/neovim/releases/latest"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            # The response is a redirect to the actual release page
            # The URL contains the version tag
            final_url = response.geturl()

            # Extract version from URL like .../releases/tag/v0.11.6
            match = re.search(r"/tag/v?([0-9]+\.[0-9]+\.[0-9]+)", final_url)
            if match:
                return match.group(1)

            # Fallback: try to read content and find version
            content = response.read().decode("utf-8")
            match = re.search(r"tag/v([0-9]+\.[0-9]+\.[0-9]+)", content)
            if match:
                return match.group(1)

        raise ValueError("raise: Could not extract version from GitHub response")

    except urllib.error.HTTPError as e:
        raise ValueError(f"raise: HTTP error {e.code} when fetching {url}: {e.reason}")
    except urllib.error.URLError as e:
        raise ValueError(f"raise: URL error when fetching {url}: {e.reason}")


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
