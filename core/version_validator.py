#!/usr/bin/env python3
"""
多源交叉验证器
用于验证AI检测到的版本信息的准确性

作者: AI Gentoo Maintainer
"""

import subprocess
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ValidationResult:
    """验证结果"""

    source_name: str
    version_found: Optional[str]
    is_valid: bool
    confidence_boost: float
    raw_data: Dict = field(default_factory=dict)


class MultiSourceValidator:
    """
    多源交叉验证器

    通过多个独立源验证版本信息，提高置信度
    """

    def __init__(self):
        self.validation_cache = {}

    async def validate_version(self, package: str, ai_result: Dict) -> Dict:
        """
        使用多个源交叉验证AI的结果

        Args:
            package: 包名（如 app-editors/neovim）
            ai_result: AI返回的结果

        Returns:
            包含验证结果的Dict
        """

        ai_version = ai_result.get("latest_version")
        ai_confidence = ai_result.get("confidence", 0.5)

        validation_results = []

        # 1. 验证GitHub releases
        github_version = await self._check_github_releases(package, ai_result)
        if github_version:
            validation_results.append(github_version)

        # 2. 验证Arch Linux
        arch_version = self._check_arch_package(package)
        if arch_version:
            validation_results.append(arch_version)

        # 3. 验证PyPI（如果是Python包）
        if package.startswith("dev-python/"):
            pypi_version = self._check_pypi_package(package)
            if pypi_version:
                validation_results.append(pypi_version)

        # 4. 验证NPM（如果是Node包）
        if package.startswith("dev-java/") or package.startswith("www-client/"):
            pass  # 可以添加更多验证

        # 计算最终置信度
        validation_matches = sum(
            1
            for r in validation_results
            if r.is_valid and r.version_found == ai_version
        )
        total_validations = len(validation_results)

        # 置信度计算：
        # AI原始置信度 * 0.6 + 验证匹配度 * 0.4
        match_ratio = (
            validation_matches / total_validations if total_validations > 0 else 0.5
        )
        final_confidence = (ai_confidence * 0.6) + (match_ratio * 0.4)

        # 如果有验证匹配，增加置信度
        if validation_matches > 0:
            final_confidence = min(0.95, final_confidence + 0.1 * validation_matches)

        return {
            "ai_result": ai_result,
            "validation_results": [r.__dict__ for r in validation_results],
            "validation_count": total_validations,
            "validation_matches": validation_matches,
            "final_confidence": round(final_confidence, 2),
            "is_verified": final_confidence >= 0.8,
            "needs_manual_review": final_confidence < 0.7,
        }

    async def _check_github_releases(
        self, package: str, ai_result: Dict
    ) -> Optional[ValidationResult]:
        """
        验证GitHub releases版本
        """

        name = package.split("/")[-1]

        # 从AI结果获取可能的GitHub URL
        source_url = ai_result.get("source_url", "")
        if "github.com" not in source_url:
            source_url = f"https://github.com/{name}/{name}"

        try:
            # 使用Firecrawl获取releases页面
            releases_url = f"{source_url}/releases"

            content = firecrawl_firecrawl_scrape(
                url=releases_url,
                formats=["markdown"],
                onlyMainContent=True,
                maxAge=3600000,
            )

            if not content:
                return None

            # 提取最新版本号
            version_match = re.search(
                r"release[/\s]*v?(\d+\.\d+\.\d+)", content, re.IGNORECASE
            )

            if version_match:
                version = version_match.group(1)
                ai_version = ai_result.get("latest_version")

                return ValidationResult(
                    source_name="github_releases",
                    version_found=version,
                    is_valid=version == ai_version,
                    confidence_boost=0.15 if version == ai_version else -0.1,
                    raw_data={"url": releases_url, "extracted_version": version},
                )

        except Exception as e:
            print(f"GitHub验证失败: {e}")

        return None

    def _check_arch_package(self, package: str) -> Optional[ValidationResult]:
        """
        验证Arch Linux包版本

        Arch Linux是滚动发行版，版本通常很新
        """

        name = package.split("/")[-1]

        try:
            # 访问Arch包页面
            url = f"https://archlinux.org/packages/extra/x86_64/{name}/"

            content = firecrawl_firecrawl_scrape(
                url=url, formats=["markdown"], onlyMainContent=True, maxAge=3600000
            )

            if not content:
                # 尝试community仓库
                url = f"https://archlinux.org/packages/community/x86_64/{name}/"
                content = firecrawl_firecrawl_scrape(
                    url=url, formats=["markdown"], onlyMainContent=True, maxAge=3600000
                )

            if not content:
                return None

            # 提取版本号
            version_patterns = [
                r"Current[\s]*Version:?[\s]*(\d+\.\d+\.\d+)",
                r"Package[\s]*Version:?[\s]*(\d+\.\d+\.\d+)",
                r"(\d+\.\d+\.\d+)-(\d+)",  # 版本-构建号
            ]

            for pattern in version_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    if match.lastindex == 2:
                        version = f"{match.group(1)}-{match.group(2)}"
                    else:
                        version = match.group(1)

                    return ValidationResult(
                        source_name="arch_linux",
                        version_found=version,
                        is_valid=True,  # Arch版本作为参考，不直接比较
                        confidence_boost=0.1,
                        raw_data={"url": url, "arch_version": version},
                    )

        except Exception as e:
            print(f"Arch验证失败: {e}")

        return None

    def _check_pypi_package(self, package: str) -> Optional[ValidationResult]:
        """
        验证PyPI包版本（针对dev-python/类别）
        """

        name = package.split("/")[-1]
        pypi_name = name.replace("_", "-")

        try:
            url = f"https://pypi.org/pypi/{pypi_name}/json"

            # 使用web fetch获取JSON
            content = webfetch(url=url, format="text")

            if content:
                import json as json_module

                data = json_module.loads(content)
                version = data.get("info", {}).get("version")

                if version:
                    return ValidationResult(
                        source_name="pypi",
                        version_found=version,
                        is_valid=True,
                        confidence_boost=0.1,
                        raw_data={"url": url, "pypi_version": version},
                    )

        except Exception as e:
            print(f"PyPI验证失败: {e}")

        return None

    def _check_npm_package(self, package: str) -> Optional[ValidationResult]:
        """
        验证NPM包版本（针对dev-java/或www-client/类别）
        """

        name = package.split("/")[-1]

        try:
            url = f"https://registry.npmjs.org/{name}/latest"

            content = webfetch(url=url, format="text")

            if content:
                import json as json_module

                data = json_module.loads(content)
                version = data.get("version")

                if version:
                    return ValidationResult(
                        source_name="npm",
                        version_found=version,
                        is_valid=True,
                        confidence_boost=0.1,
                        raw_data={"url": url, "npm_version": version},
                    )

        except Exception as e:
            print(f"NPM验证失败: {e}")

        return None


def validate_ai_result(package: str, ai_result: Dict) -> Dict:
    """
    便捷函数：验证AI版本检测结果

    Usage:
        validation = validate_ai_result(
            "app-editors/neovim",
            {"latest_version": "0.10.0", "confidence": 0.8}
        )
        print(f"验证通过: {validation['is_verified']}")
    """
    import asyncio

    validator = MultiSourceValidator()
    return asyncio.run(validator.validate_version(package, ai_result))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python version_validator.py <AI结果JSON>")
        sys.exit(1)

    ai_result = json.loads(sys.argv[1])
    package = ai_result.get("package", "unknown")

    result = validate_ai_result(package, ai_result)

    print(f"\n{'=' * 60}")
    print(f"验证结果: {package}")
    print(f"{'=' * 60}")
    print(f"AI置信度: {ai_result.get('confidence', 0.0)}")
    print(f"最终置信度: {result['final_confidence']}")
    print(f"验证通过: {'是' if result['is_verified'] else '否'}")
    print(f"需要人工复核: {'是' if result['needs_manual_review'] else '否'}")
    print(f"{'=' * 60}")
