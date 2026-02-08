#!/usr/bin/env python3
"""
AI驱动的上游版本检查器
使用k2.5 free模型智能搜索和解析上游版本

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

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SearchStrategy(Enum):
    """搜索策略枚举"""

    GITHUB_RELEASES = "github_releases"
    GITLAB_RELEASES = "gitlab_releases"
    SOURCEFORGE = "sourceforge"
    OFFICIAL_DOWNLOAD = "official_download"
    ARCH_LINUX = "arch_linux"
    NPM = "npm"
    PYPI = "pypi"
    CRAN = "cran"
    CUSTOM = "custom"


@dataclass
class UpstreamSource:
    """上游版本源信息"""

    url: str
    strategy: SearchStrategy
    version_pattern: Optional[str] = None
    last_verified: Optional[datetime] = None


@dataclass
class VersionCheckResult:
    """版本检查结果"""

    package_name: str
    category: str
    current_version: str
    latest_version: Optional[str] = None
    sources_checked: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    release_date: Optional[str] = None
    source_url: Optional[str] = None
    download_url: Optional[str] = None
    raw_ai_response: str = ""
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    needs_update: bool = False


class AIUpstreamChecker:
    """
    AI驱动的上游版本检查器

    使用k2.5 free模型（通过Perplexity/Firecrawl等工具）
    自动检测上游软件包版本
    """

    # 已知上游源映射
    KNOWN_SOURCES = {
        "app-editors/neovim": {
            "primary": "https://github.com/neovim/neovim/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "app-editors/vim": {
            "primary": "https://github.com/vim/vim/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "dev-vcs/git": {
            "primary": "https://git-scm.com/download",
            "strategy": SearchStrategy.OFFICIAL_DOWNLOAD,
        },
        "app-misc/htop": {
            "primary": "https://github.com/htop-dev/htop/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "app-misc/fd": {
            "primary": "https://github.com/sharkdp/fd/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "sys-apps/ripgrep": {
            "primary": "https://github.com/BurntSushi/ripgrep/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "app-text/bat": {
            "primary": "https://github.com/sharkdp/bat/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "sys-apps/exa": {
            "primary": "https://github.com/ogham/exa/releases",
            "strategy": SearchStrategy.GITHUB_RELEASES,
        },
        "net-misc/curl": {
            "primary": "https://curl.se/download.html",
            "strategy": SearchStrategy.OFFICIAL_DOWNLOAD,
        },
        "net-misc/wget": {
            "primary": "https://ftp.gnu.org/gnu/wget/",
            "strategy": SearchStrategy.OFFICIAL_DOWNLOAD,
        },
    }

    def __init__(self, model: str = "k2.5-free"):
        self.model = model
        self.cache_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "version_cache.json",
        )
        self.cache = self._load_cache()

        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

    def _load_cache(self) -> Dict[str, Dict]:
        """加载版本缓存"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"警告: 无法加载缓存文件: {e}")
        return {}

    def _save_cache(self):
        """保存版本缓存"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            print(f"警告: 无法保存缓存文件: {e}")

    def get_upstream_info(self, package: str, ebuild_path: str) -> VersionCheckResult:
        """
        使用AI获取上游版本信息

        Args:
            package: 包名（如 app-editors/neovim）
            ebuild_path: ebuild文件路径

        Returns:
            VersionCheckResult: 包含版本信息的对象
        """

        # 解析包名
        parts = package.split("/")
        if len(parts) != 2:
            return VersionCheckResult(
                package_name=package,
                category="unknown",
                current_version="unknown",
                error_message=f"无效的包名格式: {package}",
            )

        category, name = parts
        current_version = self._extract_version_from_ebuild(ebuild_path)

        # 检查缓存
        cache_key = f"{package}:{current_version}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # 24小时内使用缓存
            cached_time = datetime.fromisoformat(cached.get("timestamp", "2000-01-01"))
            if (datetime.now() - cached_time).total_seconds() < 86400:
                print(f"使用缓存: {package}")
                return VersionCheckResult(**cached)

        # 分析包特征
        package_info = self._analyze_package(category, name)

        # 生成AI提示词
        prompt = self._generate_version_search_prompt(
            package=package,
            name=name,
            category=category,
            current_version=current_version,
            package_info=package_info,
        )

        # 调用AI模型
        ai_result = self._call_ai_model(prompt, package)

        # 解析结果
        version_info = self._parse_ai_response(ai_result, package, current_version)

        # 判断是否需要更新
        needs_update = self._versions_differ(
            current_version, version_info.get("latest_version")
        )

        result = VersionCheckResult(
            package_name=name,
            category=category,
            current_version=current_version,
            latest_version=version_info.get("latest_version"),
            confidence=version_info.get("confidence", 0.0),
            release_date=version_info.get("release_date"),
            source_url=version_info.get("source_url"),
            download_url=version_info.get("download_url"),
            raw_ai_response=version_info.get("raw_ai_response", ""),
            needs_update=needs_update,
        )

        # 缓存结果
        self.cache[cache_key] = {
            **result.__dict__,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_cache()

        return result

    def _analyze_package(self, category: str, name: str) -> Dict[str, Any]:
        """分析包的特征，确定搜索策略"""

        # 类型映射
        type_mappings = {
            "app-editors": "编辑器/IDE",
            "dev-vcs": "版本控制系统",
            "sys-kernel": "内核相关",
            "dev-lang": "编程语言",
            "app-shells": "Shell",
            "net-misc": "网络工具",
            "media-video": "视频工具",
            "media-sound": "音频工具",
            "app-misc": "应用程序",
            "sys-apps": "系统工具",
            "app-text": "文本工具",
            "dev-util": "开发工具",
        }

        # 可能的GitHub源
        github_guesses = [
            f"https://github.com/{name}/{name}",
            f"https://github.com/{name}",
            f"https://github.com/vim/{name}",
            f"https://github.com/htop-dev/{name}",
            f"https://github.com/sharkdp/{name}",
            f"https://github.com/BurntSushi/{name}",
            f"https://github.com/ogham/{name}",
        ]

        # 查找已知源
        full_name = f"{category}/{name}"
        known_source = self.KNOWN_SOURCES.get(full_name)

        analysis = {
            "type": type_mappings.get(category, "通用软件"),
            "name": name,
            "category": category,
            "likely_github": github_guesses,
            "known_source": known_source,
            "full_name": full_name,
        }

        return analysis

    def _generate_version_search_prompt(
        self,
        package: str,
        name: str,
        category: str,
        current_version: str,
        package_info: Dict,
    ) -> str:
        """
        生成AI版本搜索提示词

        使用json格式返回，便于解析
        """

        known = package_info.get("known_source", {})

        prompt = f"""
# Gentoo软件包上游版本搜索任务

## 任务背景
你是一个专业的Gentoo Linux软件包维护助手。任务是找到指定软件包的最新上游版本。

## 目标软件包
- **包名**: {package}
- **分类**: {package_info["type"]}
- **当前Gentoo版本**: {current_version}

## 已知的上游信息
- **发布页面**: {known.get("primary", "未知")}
- **搜索策略**: {known.get("strategy", "未知").value if known.get("strategy") else "需要搜索"}

## 搜索策略指南

### 如果你知道上游地址：
1. 访问上游的官方发布页面
2. 查看最新的稳定版本号
3. 确认下载链接是否有效
4. 检查版本发布日期

### 如果你不知道上游地址：
1. 首先尝试搜索 "{name} official website download"
2. 然后搜索 "{name} latest stable release version GitHub"
3. 检查常见的平台（GitHub Releases, GitLab等）

### 需要提取的信息：
1. **最新版本号**（例如：1.2.3，去除v前缀）
2. **版本发布日期**（YYYY-MM-DD格式）
3. **官方发布页面URL**
4. **下载链接**（用于更新SRC_URI）

## 输出格式
请严格按照以下JSON格式返回：

```json
{{
    "package": "{package}",
    "current_version": "{current_version}",
    "latest_version": "最新稳定版本号（去除v前缀）",
    "release_date": "YYYY-MM-DD 或 'unknown'",
    "source_url": "官方发布页面URL（必须提供）",
    "download_url": "最新版本的下载链接模板",
    "confidence": 0.95,
    "search_steps": [
        "步骤1: 搜索了...",
        "步骤2: 在...找到了版本号"
    ],
    "notes": "任何重要备注"
}}
```

## 重要提示
- 版本号以"v"开头的一定要去掉（如v1.2.3 → 1.2.3）
- 优先选择stable稳定版，排除beta/RC版本
- confidence反映你对结果准确性的信心（0.0-1.0）
- 如果无法找到准确版本，confidence设低并说明原因
- **source_url必须提供**，这是验证的关键

请开始搜索并返回JSON结果。
"""

        return prompt

    def _call_ai_model(self, prompt: str, package: str) -> str:
        """
        调用k2.5 free模型执行搜索

        优先级：
        1. Perplexity搜索
        2. Firecrawl网页分析
        3. WebSearch
        """

        print(f"\n{'=' * 60}")
        print(f"正在检查: {package}")
        print(f"使用模型: {self.model}")
        print(f"{'=' * 60}")

        # 提取包名用于搜索
        name = package.split("/")[-1]

        # 1. 首先尝试Perplexity搜索
        search_queries = [
            f"{name} latest stable release version official download 2024",
            f"{name} GitHub releases latest version",
            f"{name} software {package} upstream source",
        ]

        all_search_results = []

        try:
            for query in search_queries[:2]:  # 限制搜索数量
                print(f"搜索: {query}")
                result = perplexity_perplexity_search(query=query, max_results=5)
                if result:
                    all_search_results.append({"query": query, "result": result})
        except Exception as e:
            print(f"Perplexity搜索失败: {e}")

        # 2. 如果Perplexity结果不足，尝试Firecrawl
        if len(all_search_results) < 2:
            try:
                # 尝试访问GitHub releases页面
                github_url = f"https://github.com/{name}/{name}/releases"
                print(f"尝试抓取: {github_url}")

                content = firecrawl_firecrawl_scrape(
                    url=github_url,
                    formats=["markdown"],
                    onlyMainContent=True,
                    maxAge=3600000,  # 1小时缓存
                )

                if content:
                    all_search_results.append({"url": github_url, "content": content})
            except Exception as e:
                print(f"Firecrawl抓取失败: {e}")

        # 3. 综合结果
        if all_search_results:
            combined_result = {
                "package": package,
                "search_results": all_search_results,
                "analysis_prompt": prompt,
                "model": self.model,
            }
            return json.dumps(combined_result)

        # 所有方法都失败
        return json.dumps(
            {"error": "所有AI搜索方法都失败了", "confidence": 0.0, "package": package}
        )

    def _parse_ai_response(
        self, ai_response: str, package: str, current_version: str
    ) -> Dict[str, Any]:
        """
        解析AI返回的结果
        """

        try:
            # 尝试直接解析JSON
            result = json.loads(ai_response)

            # 如果包含搜索结果，需要进一步分析
            if "search_results" in result:
                # 综合分析搜索结果
                analysis = self._analyze_search_results(
                    result.get("search_results", []), package
                )
                return analysis

            return result

        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            import re

            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            match = re.search(json_pattern, ai_response, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

            # 返回原始响应
            return {"raw": ai_response, "confidence": 0.0, "error": "无法解析AI响应"}

    def _analyze_search_results(
        self, search_results: List[Dict], package: str
    ) -> Dict[str, Any]:
        """
        分析搜索结果，提取版本信息
        """

        combined_text = ""
        for result in search_results:
            if isinstance(result, dict):
                combined_text += str(result.get("result", ""))
                combined_text += str(result.get("content", ""))
            else:
                combined_text += str(result)

        # 使用Perplexity Reason进行深度分析
        analysis_prompt = f"""
你是一个Gentoo软件包维护专家。请从以下搜索结果中提取{package}的最新版本信息。

## 搜索结果
{combined_text}

## 任务
请提取：
1. 最新版本号（去除v前缀）
2. 发布日期
3. 官方发布页面URL

请直接返回JSON格式：
{{
    "package": "{package}",
    "latest_version": "版本号",
    "release_date": "YYYY-MM-DD",
    "source_url": "URL",
    "confidence": 0.9,
    "search_steps": ["从...找到版本号"]
}}
"""

        try:
            # 使用reasoning模型分析
            reasoning_result = perplexity_perplexity_reason(
                messages=[
                    {"role": "system", "content": "你是一个专业的软件版本分析助手。"},
                    {"role": "user", "content": analysis_prompt},
                ],
                strip_thinking=True,
            )

            if reasoning_result:
                try:
                    return json.loads(reasoning_result)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"Reasoning分析失败: {e}")

        # 降级：直接正则表达式提取
        return self._extract_version_regex(combined_text, package)

    def _extract_version_regex(self, text: str, package: str) -> Dict[str, Any]:
        """
        使用正则表达式从文本中提取版本号（降级方案）
        """

        name = package.split("/")[-1]

        # 版本号模式
        version_patterns = [
            rf"{name}[-_]?v?(\d+\.\d+\.\d+)",  # name-1.2.3 或 name_v1.2.3
            rf"{name}-(\d+\.\d+\.\d+)",
            rf"v(\d+\.\d+\.\d+)",
            r"(\d+\.\d+\.\d+)",
        ]

        versions_found = []
        for pattern in version_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match:
                    versions_found.append(match)

        if versions_found:
            # 返回最高版本
            latest = max(versions_found, key=lambda x: tuple(map(int, x.split("."))))
            return {
                "package": package,
                "latest_version": latest,
                "confidence": 0.3,  # 低置信度
                "source_url": "",
                "notes": "通过正则表达式提取，建议人工确认",
            }

        return {
            "package": package,
            "latest_version": None,
            "confidence": 0.0,
            "error": "无法提取版本号",
        }

    def _extract_version_from_ebuild(self, ebuild_path: str) -> str:
        """从ebuild文件中提取当前版本"""

        if not os.path.exists(ebuild_path):
            return "unknown"

        try:
            with open(ebuild_path, "r") as f:
                content = f.read()

            # 匹配版本号的各种模式
            patterns = [
                r"^(\w+)-(\d+\.\d+\.\d+(?:-r\d+)?)\.ebuild",  # 包名-版本.ebuild
                r'MY_PV="(\d+\.\d+\.\d+)"',
                r"MY_PV=\'(\d+\.\d+\.\d+)\'",
                r'VERSION="(\d+\.\d+\.\d+(?:-r\d+)?)"',
                r"VERSION=\'(\d+\.\d+\.\d+(?:-r\d+)?)\'",
                r'PV="(\d+\.\d+\.\d+)"',
                r"PV=(\d+\.\d+\.\d+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.MULTILINE)
                if match:
                    version = match.group(1) if match.lastindex == 1 else match.group(2)
                    # 清理版本号
                    version = version.replace("-r", ".r")
                    return version

            return "unknown"

        except Exception as e:
            print(f"读取ebuild失败: {ebuild_path}: {e}")
            return "unknown"

    def _versions_differ(self, current: str, latest: Optional[str]) -> bool:
        """检查版本是否不同"""

        if not latest or latest == "unknown":
            return False

        if current == "unknown":
            return True

        # 标准化版本号进行比较
        def normalize(v):
            # 移除常见前缀后缀
            v = re.sub(r"^v", "", v)
            v = re.sub(r"-r\d+$", "", v)
            v = re.sub(r"_\d+$", "", v)
            return v

        return normalize(current) != normalize(latest)


# 便捷函数
def check_package_version(package: str, ebuild_path: str) -> VersionCheckResult:
    """
    检查单个软件包的上游版本

    Usage:
        result = check_package_version(
            "app-editors/neovim",
            "/path/to/neovim-0.9.5.ebuild"
        )
        if result.needs_update:
            print(f"需要更新: {result.current_version} → {result.latest_version}")
    """
    checker = AIUpstreamChecker()
    return checker.get_upstream_info(package, ebuild_path)


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) < 2:
        print("用法: python version_checker.py <包名>")
        print("示例: python version_checker.py app-editors/neovim")
        sys.exit(1)

    package = sys.argv[1]

    # 查找ebuild
    parts = package.split("/")
    if len(parts) == 2:
        category, name = parts
        ebuild_path = f"/var/db/repos/gentoo/{category}/{name}/{name}-*.ebuild"

        # 找到最新的ebuild
        import glob

        ebuilds = glob.glob(ebuild_path)
        if ebuilds:
            ebuild_path = sorted(ebuilds)[-1]  # 使用最新的
        else:
            # 检查AI仓库
            ebuild_path = f"/var/db/repos/gentoo-ai-update-repo/{package.split('/')[0]}/{package.split('/')[1]}/*.ebuild"
            ebuilds = glob.glob(ebuild_path)
            if ebuilds:
                ebuild_path = sorted(ebuilds)[-1]
            else:
                print(f"找不到ebuild文件: {package}")
                sys.exit(1)

    result = check_package_version(package, ebuild_path)

    print(f"\n{'=' * 60}")
    print(f"检查结果: {package}")
    print(f"{'=' * 60}")
    print(f"当前版本: {result.current_version}")
    print(f"最新版本: {result.latest_version}")
    print(f"置信度: {result.confidence}")
    print(f"需要更新: {'是' if result.needs_update else '否'}")
    if result.source_url:
        print(f"发布页面: {result.source_url}")
    if result.release_date:
        print(f"发布日期: {result.release_date}")
    print(f"{'=' * 60}")
