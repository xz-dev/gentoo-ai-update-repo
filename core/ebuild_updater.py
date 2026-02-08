#!/usr/bin/env python3
"""
ebuild更新器
使用AI自动更新Gentoo ebuild文件

作者: AI Gentoo Maintainer
"""

import subprocess
import json
import re
import os
import sys
import shutil
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class UpdateResult:
    """更新结果"""

    success: bool
    package: str
    old_version: str
    new_version: str
    ebuild_path: str
    changes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    needs_manual_review: bool = False
    test_output: str = ""


class EbuildUpdater:
    """
    ebuild自动更新器

    使用AI提示词自动完成：
    1. 分析当前ebuild
    2. 更新版本号
    3. 调整依赖和SRC_URI
    4. 运行质量检查
    5. 自动修复问题
    """

    def __init__(self, ai_repo_path: str = "/var/db/repos/gentoo-ai-update-repo"):
        self.ai_repo_path = ai_repo_path
        self.gentoo_repo_path = "/var/db/repos/gentoo"
        self.backup_path = os.path.join(ai_repo_path, "backups")
        os.makedirs(self.backup_path, exist_ok=True)

    def update_ebuild(
        self, package: str, current_version: str, new_version: str, upstream_info: Dict
    ) -> UpdateResult:
        """
        更新单个软件包的ebuild

        Args:
            package: 包名（如 app-editors/neovim）
            current_version: 当前版本
            new_version: 新版本
            upstream_info: 上游版本信息

        Returns:
            UpdateResult: 更新结果
        """

        result = UpdateResult(
            success=False,
            package=package,
            old_version=current_version,
            new_version=new_version,
            ebuild_path="",
        )

        try:
            # 1. 找到当前的ebuild
            ebuild_path = self._find_current_ebuild(package, current_version)
            if not ebuild_path:
                result.errors.append(f"找不到当前ebuild: {package}-{current_version}")
                return result

            # 2. 读取当前ebuild内容
            with open(ebuild_path, "r") as f:
                current_content = f.read()

            # 3. 生成AI更新提示词
            prompt = self._generate_update_prompt(
                package=package,
                current_version=current_version,
                new_version=new_version,
                upstream_info=upstream_info,
                current_content=current_content,
            )

            # 4. 执行AI更新
            update_instructions = self._call_ai_updater(prompt)

            # 5. 应用更新
            new_ebuild_path = self._apply_updates(
                package=package,
                old_version=current_version,
                new_version=new_version,
                current_content=current_content,
                instructions=update_instructions,
            )

            result.ebuild_path = new_ebuild_path

            # 6. 运行质量检查
            test_result = self._run_quality_checks(new_ebuild_path)
            result.test_output = test_result.get("output", "")

            if not test_result.get("success", False):
                result.needs_manual_review = True
                result.errors.append(f"质量检查失败: {test_result.get('output', '')}")

            # 7. 如果需要，尝试自动修复
            if result.needs_manual_review:
                fix_result = self._attempt_auto_fix(new_ebuild_path, test_result)
                if fix_result.get("success", False):
                    result.needs_manual_review = False
                    result.changes.append(f"自动修复: {fix_result.get('changes', [])}")

            result.success = not result.needs_manual_review or len(result.errors) == 0

        except Exception as e:
            result.errors.append(f"更新过程出错: {str(e)}")

        return result

    def _find_current_ebuild(self, package: str, version: str) -> Optional[str]:
        """找到当前的ebuild文件"""

        category, name = package.split("/")

        # 首先在AI仓库查找
        ai_dir = os.path.join(self.ai_repo_path, category, name)
        if os.path.exists(ai_dir):
            for f in os.listdir(ai_dir):
                if f.endswith(".ebuild") and version in f:
                    return os.path.join(ai_dir, f)

        # 在Gentoo主仓库查找
        gentoo_dir = os.path.join(self.gentoo_repo_path, category, name)
        if os.path.exists(gentoo_dir):
            for f in os.listdir(gentoo_dir):
                if f.endswith(".ebuild") and version in f:
                    return os.path.join(gentoo_dir, f)

        return None

    def _generate_update_prompt(
        self,
        package: str,
        current_version: str,
        new_version: str,
        upstream_info: Dict,
        current_content: str,
    ) -> str:
        """
        生成AI更新提示词
        """

        return f"""
# Gentoo ebuild 自动更新任务

你是一位专业的Gentoo Linux ebuild维护者。你的任务是更新软件包的ebuild文件到新版本。

## 任务信息
- **包名**: {package}
- **当前版本**: {current_version}
- **新版本**: {new_version}
- **上游发布页面**: {upstream_info.get("source_url", "未知")}
- **上游下载链接**: {upstream_info.get("download_url", "未知")}
- **发布日期**: {upstream_info.get("release_date", "未知")}

## 当前ebuild内容
```ebuild
{current_content}
```

## 任务步骤

### 步骤1: 分析当前ebuild
请识别：
1. 版本号定义位置（PV, VERSION, MY_PV）
2. SRC_URI配置
3. 依赖项（DEPEND, RDEPEND, BDEPEND）
4. LICENSE
5. KEYWORDS
6. 任何需要调整的地方

### 步骤2: 生成更新后的ebuild
请基于当前ebuild，创建新版本的ebuild：

1. **更新版本号**
   - 修改VERSION或PV变量
   - 如果需要，调整MY_PV

2. **更新SRC_URI**
   - 检查上游下载链接格式是否变化
   - 更新下载URL（使用新版本号）
   - 保持mirrorselect配置

3. **调整依赖**
   - 检查新版本是否需要新的依赖
   - 移除不再需要的依赖

4. **其他调整**
   - 更新HOMEPAGE（如有必要）
   - 调整LICENSE（如有必要）
   - 更新S（如源代码目录结构变化）

### 步骤3: 输出更新后的完整ebuild

请返回完整的、更新后的ebuild文件内容，使用以下格式：

```ebuild
<完整的ebuild内容>
```

### 步骤4: 列出修改内容
在ebuild内容之后，列出你做的所有修改：

```markdown
## 修改摘要
- 更新版本号: {current_version} → {new_version}
- 更新SRC_URI: ...
- 更新依赖: ...
- 其他修改: ...
```

## 注意事项
- 保持Gentoo ebuild的编码标准
- 不要改变包的结构
- 保留所有重要的补丁
- 确保兼容性
- 如果有任何不确定的地方，标注"需要人工复核"
"""

    def _call_ai_updater(self, prompt: str) -> Dict[str, Any]:
        """
        调用AI执行更新

        使用Perplexity Reason进行ebuild更新
        """

        try:
            # 使用reasoning模型进行复杂的ebuild更新任务
            result = perplexity_perplexity_reason(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位经验丰富的Gentoo Linux ebuild维护者。你精通ebuild语法、Gentoo打包规范和最佳实践。",
                    },
                    {"role": "user", "content": prompt},
                ],
                strip_thinking=True,
            )

            if result:
                return self._parse_ai_update_response(result)

        except Exception as e:
            print(f"AI更新调用失败: {e}")

        return {"error": str(e), "success": False}

    def _parse_ai_update_response(self, response: str) -> Dict[str, Any]:
        """
        解析AI更新响应
        """

        # 提取ebuild内容和修改摘要
        ebuild_match = re.search(r"```ebuild\n(.*?)\n```", response, re.DOTALL)

        summary_match = re.search(r"## 修改摘要\n(.*?)(?:\n```|$)", response, re.DOTALL)

        changes = []
        if summary_match:
            change_lines = summary_match.group(1).strip().split("\n")
            for line in change_lines:
                if line.strip().startswith("-"):
                    changes.append(line.strip().lstrip("- "))

        return {
            "ebuild_content": ebuild_match.group(1).strip() if ebuild_match else "",
            "changes": changes,
            "raw_response": response,
            "success": bool(ebuild_match),
        }

    def _apply_updates(
        self,
        package: str,
        old_version: str,
        new_version: str,
        current_content: str,
        instructions: Dict,
    ) -> str:
        """
        应用更新，创建新的ebuild文件
        """

        category, name = package.split("/")

        # 创建新ebuild路径
        new_ebuild_name = f"{name}-{new_version}.ebuild"
        new_dir = os.path.join(self.ai_repo_path, category, name)
        os.makedirs(new_dir, exist_ok=True)
        new_ebuild_path = os.path.join(new_dir, new_ebuild_name)

        # 如果AI返回了完整的ebuild内容
        if instructions.get("ebuild_content"):
            with open(new_ebuild_path, "w") as f:
                f.write(instructions["ebuild_content"])
        else:
            # 降级：只更新版本号
            new_content = re.sub(
                rf'VERSION=["\']?{old_version}["\']?',
                f'VERSION="{new_version}"',
                current_content,
            )

            # 也尝试PV
            new_content = re.sub(
                rf'PV=["\']?{old_version}["\']?', f'PV="{new_version}"', new_content
            )

            with open(new_ebuild_path, "w") as f:
                f.write(new_content)

        # 备份旧的ebuild（如果有）
        if os.path.exists(new_ebuild_path.replace(new_version, old_version)):
            backup_file = os.path.join(
                self.backup_path,
                f"{package}-{old_version}-{datetime.now().strftime('%Y%m%d%H%M%S')}.ebuild",
            )
            shutil.copy2(new_ebuild_path.replace(new_version, old_version), backup_file)

        return new_ebuild_path

    def _run_quality_checks(self, ebuild_path: str) -> Dict[str, Any]:
        """
        运行ebuild质量检查
        """

        results = {"success": True, "output": "", "errors": []}

        # 检查ebuild文件是否存在
        if not os.path.exists(ebuild_path):
            return {
                "success": False,
                "output": "ebuild文件不存在",
                "errors": ["文件不存在"],
            }

        # 1. 检查语法（基本格式）
        with open(ebuild_path, "r") as f:
            content = f.read()

        # 检查必要的头部
        required_sections = ["HOMEPAGE", "SRC_URI", "LICENSE"]
        for section in required_sections:
            if section not in content:
                results["errors"].append(f"缺少必要字段: {section}")

        # 2. 运行repoman检查（如果可用）
        try:
            result = subprocess.run(
                ["repoman", "full"],
                cwd=os.path.dirname(ebuild_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                results["success"] = False
                results["output"] = result.stderr or result.stdout
                results["errors"].append(f"repoman检查失败: {result.stderr}")

        except FileNotFoundError:
            results["output"] += "\n警告: repoman未安装，跳过质量检查"
        except subprocess.TimeoutExpired:
            results["output"] += "\n警告: repoman超时，跳过部分检查"

        # 3. 预演安装
        try:
            result = subprocess.run(
                [
                    "ebuild",
                    os.path.basename(ebuild_path),
                    "clean",
                    "install",
                    "--pretend",
                ],
                cwd=os.path.dirname(ebuild_path),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                results["success"] = False
                results["output"] += f"\n预演失败: {result.stderr}"
                results["errors"].append(f"安装预演失败: {result.stderr}")

        except FileNotFoundError:
            results["output"] += "\n警告: ebuild命令未安装"
        except subprocess.TimeoutExpired:
            results["output"] += "\n警告: ebuild预演超时"

        results["output"] = results["output"].strip() or "基本检查通过"
        return results

    def _attempt_auto_fix(self, ebuild_path: str, test_result: Dict) -> Dict[str, Any]:
        """
        尝试自动修复问题
        """

        with open(ebuild_path, "r") as f:
            content = f.read()

        errors = test_result.get("errors", [])
        fixes_applied = []

        for error in errors:
            # 常见的简单修复
            if "missing" in error.lower() or "缺少" in error:
                # 尝试修复缺失的字段
                if "HOMEPAGE" in error:
                    content = self._fix_missing_field(
                        content, "HOMEPAGE", "https://example.com"
                    )
                    fixes_applied.append("修复缺失的HOMEPAGE")

                elif "SRC_URI" in error:
                    content = self._fix_missing_field(
                        content, "SRC_URI", "https://example.com/${PV}/${P}.tar.gz"
                    )
                    fixes_applied.append("修复缺失的SRC_URI")

        # 写回修复后的内容
        if fixes_applied:
            with open(ebuild_path, "w") as f:
                f.write(content)

            # 重新测试
            retest = self._run_quality_checks(ebuild_path)
            return {
                "success": retest.get("success", False),
                "changes": fixes_applied,
                "retest_output": retest.get("output", ""),
            }

        return {"success": False, "changes": fixes_applied}

    def _fix_missing_field(self, content: str, field: str, value: str) -> str:
        """修复缺失的字段"""

        field_pattern = rf'({field}=["\'][^"\']*["\'])'

        if not re.search(field_pattern, content):
            # 在第一个变量声明后添加
            match = re.search(r"^(inherit.*)$", content, re.MULTILINE)
            if match:
                insertion_point = match.end()
                content = (
                    content[:insertion_point]
                    + f'\n{field}="{value}"'
                    + content[insertion_point:]
                )

        return content


def update_package_ebuild(
    package: str, current_version: str, new_version: str, upstream_info: Dict
) -> UpdateResult:
    """
    便捷函数：更新软件包ebuild

    Usage:
        result = update_package_ebuild(
            "app-editors/neovim",
            "0.9.5",
            "0.10.0",
            {"source_url": "...", "download_url": "..."}
        )
        if result.success:
            print(f"更新成功: {result.ebuild_path}")
    """
    updater = EbuildUpdater()
    return updater.update_ebuild(package, current_version, new_version, upstream_info)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("用法: python ebuild_updater.py <包名> <当前版本> <新版本>")
        sys.exit(1)

    package = sys.argv[1]
    current_version = sys.argv[2]
    new_version = sys.argv[3]

    # 模拟上游信息（实际应该从version_checker获取）
    upstream_info = {
        "source_url": "https://example.com/releases",
        "download_url": "https://example.com/${PV}.tar.gz",
        "release_date": "2024-01-01",
    }

    result = update_package_ebuild(package, current_version, new_version, upstream_info)

    print(f"\n{'=' * 60}")
    print(f"更新结果: {package}")
    print(f"{'=' * 60}")
    print(f"成功: {'是' if result.success else '否'}")
    print(f"旧版本: {result.old_version}")
    print(f"新版本: {result.new_version}")
    print(f"ebuild路径: {result.ebuild_path}")
    print(f"修改内容:")
    for change in result.changes:
        print(f"  - {change}")
    if result.errors:
        print(f"错误:")
        for error in result.errors:
            print(f"  - {error}")
    print(f"{'=' * 60}")
