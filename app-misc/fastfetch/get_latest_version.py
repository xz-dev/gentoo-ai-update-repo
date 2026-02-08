#!/usr/bin/env python3
"""Fetch the latest stable version of app-misc/fastfetch from GitHub."""

import json
import os
import re
import sys
import urllib.request
from urllib.error import URLError, HTTPError

GITHUB_API_URL = "https://api.github.com/repos/fastfetch-cli/fastfetch/releases/latest"
GITHUB_TAGS_URL = "https://api.github.com/repos/fastfetch-cli/fastfetch/tags"
GITHUB_RELEASES_URL = "https://github.com/fastfetch-cli/fastfetch/releases/latest"


def make_api_request(url, timeout=30):
    """Make authenticated request to GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "gentoo-get-latest-version/1.0",
    }

    # Use GitHub token if available (from environment variable)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
        print("Using GITHUB_TOKEN from environment", file=sys.stderr)

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 403:
            print(
                f"Error fetching from GitHub API: HTTP Error 403: rate limit exceeded",
                file=sys.stderr,
            )
            raise RuntimeError("Failed to fetch release data from GitHub API")
        elif e.code == 404:
            print(
                f"Error fetching from GitHub API: HTTP Error 404: not found",
                file=sys.stderr,
            )
            raise RuntimeError("API endpoint not found")
        else:
            print(
                f"Error fetching from GitHub API: HTTP Error {e.code}", file=sys.stderr
            )
            raise RuntimeError(f"GitHub API returned HTTP {e.code}")
    except URLError as e:
        print(f"Error fetching from GitHub API: {e}", file=sys.stderr)
        raise RuntimeError(f"Failed to connect to GitHub API: {e}")


def fetch_from_web():
    """Fetch version from GitHub web page (fallback when API is rate limited)."""
    print("Falling back to web scraping...", file=sys.stderr)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
    }

    req = urllib.request.Request(GITHUB_RELEASES_URL, headers=headers, method="GET")

    try:
        # Follow redirects
        redirect_handler = urllib.request.HTTPRedirectHandler()
        opener = urllib.request.build_opener(redirect_handler)
        urllib.request.install_opener(opener)

        with urllib.request.urlopen(req, timeout=30) as response:
            final_url = response.geturl()
            print(f"Final URL after redirect: {final_url}", file=sys.stderr)

            # Extract version from URL
            match = re.search(r"/releases/tag/(?:v)?([^/]+)$", final_url)
            if match:
                tag_name = match.group(1)
                print(f"Found tag from redirect URL: {tag_name}", file=sys.stderr)
                return tag_name

            # Try parsing HTML content
            html = response.read().decode("utf-8")

            # Look for version in page title or content
            title_match = re.search(
                r"<title>\s*Release\s+(?:v)?([\d.]+)", html, re.IGNORECASE
            )
            if title_match:
                version = title_match.group(1)
                print(f"Found version from page title: {version}", file=sys.stderr)
                return version

            # Look for version in URL patterns in the HTML
            version_match = re.search(r'/releases/tag/(?:v)?([\d.]+)"', html)
            if version_match:
                version = version_match.group(1)
                print(f"Found version from HTML: {version}", file=sys.stderr)
                return version

    except Exception as e:
        print(f"Error fetching from web: {e}", file=sys.stderr)

    raise RuntimeError("Failed to fetch version from web fallback")


def fetch_latest_version():
    """Fetch latest stable version from GitHub releases API."""
    tag_name = None

    try:
        # Try releases API first
        data = make_api_request(GITHUB_API_URL)

        # Get the tag name
        tag_name = data.get("tag_name")
        if not tag_name:
            print("No tag_name found in release data", file=sys.stderr)
            raise RuntimeError("No tag_name found in GitHub release")

        print(f"Found tag from API: {tag_name}", file=sys.stderr)

        # Check if this is a pre-release
        if data.get("prerelease", False):
            print(f"Warning: {tag_name} is marked as pre-release", file=sys.stderr)
            raise RuntimeError(f"Latest release {tag_name} is a pre-release, skipping")

    except RuntimeError:
        # Fallback 1: try tags API (different rate limit bucket)
        print(f"Falling back to tags API...", file=sys.stderr)
        try:
            tags_data = make_api_request(GITHUB_TAGS_URL)
            if not tags_data:
                raise RuntimeError("No tags found in repository")

            # Find the first non-prerelease tag
            for tag in tags_data:
                tag_name = tag.get("name", "")
                # Skip pre-release tags (containing alpha, beta, rc, pre, dev)
                if re.search(r"-(alpha|beta|rc|pre|dev)", tag_name, re.I):
                    print(f"Skipping pre-release tag: {tag_name}", file=sys.stderr)
                    continue
                print(f"Found tag: {tag_name}", file=sys.stderr)
                break
            else:
                # If all tags are pre-releases, just use the first one
                tag_name = tags_data[0].get("name", "")
                print(
                    f"All tags appear to be pre-releases, using: {tag_name}",
                    file=sys.stderr,
                )

        except RuntimeError:
            # Fallback 2: web scraping
            tag_name = fetch_from_web()

    # Remove 'v' prefix if present
    version = re.sub(r"^v", "", tag_name)

    # Validate version format (should be x.y.z or similar)
    if not re.match(r"^\d[\d.]*$", version):
        print(f"Warning: Unexpected version format: {version}", file=sys.stderr)
        raise RuntimeError(f"Invalid version format: {version}")

    return version


def main():
    try:
        version = fetch_latest_version()
        print(version)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
