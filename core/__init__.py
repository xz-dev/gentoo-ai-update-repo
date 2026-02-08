"""
Gentoo AI软件包维护系统 - 核心模块
"""

from .version_checker import (
    AIUpstreamChecker,
    VersionCheckResult,
    UpstreamSource,
    SearchStrategy,
)
from .version_validator import MultiSourceValidator
from .ebuild_updater import EbuildUpdater

__version__ = "1.0.0"
__author__ = "AI Gentoo Maintainer"

__all__ = [
    "AIUpstreamChecker",
    "VersionCheckResult",
    "UpstreamSource",
    "SearchStrategy",
    "MultiSourceValidator",
    "EbuildUpdater",
]
