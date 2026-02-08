#!/usr/bin/env python3
"""
Gentoo AI 上游版本检查器 - Python主脚本

功能:
- 使用AI自动检测上游软件版本
- 支持批量和单包检查
- 生成检查报告

作者: AI Gentoo Maintainer
"""

import os
import sys
import json
import argparse
import glob
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Any

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.version_checker import AIUpstreamChecker, check_package_version
from core.version_validator import MultiSourceValidator


class UpstreamCheckerCLI:
    """上游版本检查器命令行接口"""

    def __init__(self):
        self.script_dir = Path(__file__).parent.parent
        self.data_dir = self.script_dir / "data"
        self.log_dir = self.script_dir / "logs"
        self.config_file = self.data_dir / "packages_to_monitor.txt"

        # 创建目录
        self.data_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)

        self.checker = AIUpstreamChecker()
        self.validator = MultiSourceValidator()

    def load_packages(self) -> List[str]:
        """加载要检查的包列表"""
        packages = []

        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        packages.append(line)

        # 如果没有配置文件，扫描AI仓库中的包
        if not packages:
            packages = self._scan_ai_repo()

        return packages

    def _scan_ai_repo(self) -> List[str]:
        """扫描AI仓库中的ebuild"""
        packages = []
        ai_repo = self.script_dir

        for category_dir in ai_repo.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("."):
                for package_dir in category_dir.iterdir():
                    if package_dir.is_dir():
                        package_name = f"{category_dir.name}/{package_dir.name}"
                        packages.append(package_name)

        return packages

    def find_ebuild(self, package: str) -> Optional[str]:
        """查找包的ebuild文件"""

        parts = package.split("/")
        if len(parts) != 2:
            return None

        category, name = parts

        # 首先在AI仓库查找
        ai_path = self.script_dir / category / name
        if ai_path.exists():
            ebuilds = list(ai_path.glob("*.ebuild"))
            if ebuilds:
                return str(sorted(ebuilds)[-1])  # 返回最新的

        # 在Gentoo主仓库查找
        gentoo_path = Path("/var/db/repos/gentoo") / category / name
        if gentoo_path.exists():
            ebuilds = list(gentoo_path.glob("*.ebuild"))
            if ebuilds:
                return str(sorted(ebuilds)[-1])

        return None

    def check_single_package(
        self, package: str, verbose: bool = False
    ) -> Dict[str, Any]:
        """检查单个包"""

        result: Dict[str, Any] = {
            "package": package,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 查找ebuild
            ebuild_path = self.find_ebuild(package)

            if not ebuild_path:
                result["status"] = "not_found"
                result["error"] = "找不到ebuild文件"
                return result

            result["ebuild_path"] = ebuild_path

            # 获取上游版本信息
            version_info = self.checker.get_upstream_info(package, ebuild_path)

            # 提取需要的信息（处理dataclass）
            result["current_version"] = version_info.current_version
            result["latest_version"] = version_info.latest_version
            result["confidence"] = version_info.confidence
            result["source_url"] = version_info.source_url or ""
            result["release_date"] = version_info.release_date or ""
            result["needs_update"] = version_info.needs_update

            # 验证结果（需要同步调用）
            import asyncio

            validation = asyncio.run(
                self.validator.validate_version(package, version_info.__dict__)
            )
            result["validation"] = validation

            # 最终状态
            if version_info.needs_update and validation.get("is_verified", False):
                result["status"] = "needs_update"
            elif version_info.needs_update:
                result["status"] = "needs_review"
            else:
                result["status"] = "up_to_date"

            if verbose:
                print(f"  当前版本: {version_info.current_version}")
                print(f"  最新版本: {version_info.latest_version}")
                print(f"  置信度: {version_info.confidence:.0%}")
                print(f"  状态: {result['status']}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def check_all_packages(self, packages: List[str], max_workers: int = 3) -> Dict:
        """批量检查所有包"""

        results = {
            "timestamp": datetime.now().isoformat(),
            "total_packages": len(packages),
            "packages": [],
        }

        print(f"\n{'=' * 70}")
        print(f"开始检查 {len(packages)} 个软件包")
        print(f"使用模型: k2.5 free")
        print(f"{'=' * 70}\n")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.check_single_package, pkg): pkg for pkg in packages
            }

            for future in as_completed(futures):
                package = futures[future]

                try:
                    result = future.result()
                    results["packages"].append(result)

                    # 实时显示结果
                    status_emoji = result.get("status") or "unknown"
                    status_symbol = {
                        "needs_update": "🔄",
                        "needs_review": "⚠️",
                        "up_to_date": "✅",
                        "not_found": "❌",
                        "error": "💥",
                    }.get(status_emoji, "❓")

                    current = result.get("current_version", "N/A")
                    latest = result.get("latest_version", "N/A")
                    confidence = result.get("confidence", 0)

                    print(
                        f"{status_symbol} {package:30s} | {current:15s} → {latest:15s} | {confidence:.0%}"
                    )

                except Exception as e:
                    print(f"💥 {package:30s} | 错误: {e}")

        # 统计
        results["needs_update"] = sum(
            1
            for p in results["packages"]
            if p.get("status") in ["needs_update", "needs_review"]
        )
        results["up_to_date"] = sum(
            1 for p in results["packages"] if p.get("status") == "up_to_date"
        )
        results["failed"] = sum(
            1 for p in results["packages"] if p.get("status") in ["not_found", "error"]
        )

        print(f"\n{'=' * 70}")
        print(f"检查完成!")
        print(f"  需要更新: {results['needs_update']}")
        print(f"  已是最新: {results['up_to_date']}")
        print(f"  检查失败: {results['failed']}")
        print(f"{'=' * 70}\n")

        return results

    def save_results(self, results: Dict):
        """保存检查结果"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"check_result_{timestamp}.json"

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"结果已保存: {log_file}")
        return str(log_file)

    def generate_report(self, results: Dict) -> str:
        """生成Markdown报告"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# Gentoo AI 包维护报告\n")
            f.write(f"\n")
            f.write(f"生成时间: {results['timestamp']}\n")
            f.write(f"使用模型: k2.5 free\n")
            f.write(f"\n")

            f.write(f"## 统计信息\n")
            f.write(f"- 总包数: {results['total_packages']}\n")
            f.write(f"- 需要更新: {results['needs_update']}\n")
            f.write(f"- 已是最新: {results['up_to_date']}\n")
            f.write(f"- 检查失败: {results['failed']}\n")
            f.write(f"\n")

            if results.get("packages"):
                f.write(f"## 详细结果\n")
                f.write(f"\n")
                f.write(f"| 包名 | 当前版本 | 最新版本 | 置信度 | 状态 |\n")
                f.write(f"|------|----------|----------|--------|------|\n")

                for pkg in sorted(
                    results["packages"], key=lambda x: x.get("status", "")
                ):
                    status = pkg.get("status", "unknown")
                    status_emoji = {
                        "needs_update": "🔄 需要更新",
                        "needs_review": "⚠️ 需复核",
                        "up_to_date": "✅ 最新",
                        "not_found": "❌ 未找到",
                        "error": "💥 错误",
                    }.get(status, "❓ 未知")

                    current = pkg.get("current_version", "N/A")
                    latest = pkg.get("latest_version", "N/A")
                    confidence = pkg.get("confidence", 0)

                    f.write(
                        f"| {pkg.get('package', 'N/A')} | {current} | {latest} | {confidence:.0%} | {status_emoji} |\n"
                    )

            f.write(f"\n---\n")
            f.write(f"由 Gentoo AI 包维护系统自动生成\n")

        print(f"报告已生成: {report_file}")
        return str(report_file)


def main():
    """主函数"""

    parser = argparse.ArgumentParser(
        description="Gentoo AI 上游版本检查器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                      # 检查所有配置的包
  %(prog)s app-editors/neovim   # 检查单个包
  %(prog)s --verbose            # 显示详细输出
  %(prog)s --report             # 生成报告
        """,
    )

    parser.add_argument("package", nargs="?", default=None, help="要检查的包名（可选）")

    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细输出")

    parser.add_argument("--report", "-r", action="store_true", help="生成Markdown报告")

    parser.add_argument(
        "--workers", "-w", type=int, default=3, help="并行工作数（默认: 3）"
    )

    parser.add_argument("--config", "-c", type=str, default=None, help="指定配置文件")

    args = parser.parse_args()

    cli = UpstreamCheckerCLI()

    if args.config:
        cli.config_file = Path(args.config)

    # 单包检查
    if args.package:
        print(f"\n检查单个包: {args.package}")
        result = cli.check_single_package(args.package, args.verbose)

        print(f"\n结果:")
        print(f"  状态: {result.get('status', 'unknown')}")
        print(f"  当前版本: {result.get('current_version', 'N/A')}")
        print(f"  最新版本: {result.get('latest_version', 'N/A')}")
        print(f"  置信度: {result.get('confidence', 0):.0%}")
        print(f"  发布页面: {result.get('source_url', 'N/A')}")

        if result.get("needs_update"):
            print(f"\n🔄 需要更新!")
        else:
            print(f"\n✅ 已是最新版本")

        return

    # 批量检查
    packages = cli.load_packages()

    if not packages:
        print("没有找到要检查的包!")
        print(f"请在 {cli.config_file} 中添加包列表")
        print("或者确保AI仓库中有ebuild文件")
        return

    results = cli.check_all_packages(packages, args.workers)

    # 保存结果
    cli.save_results(results)

    # 生成报告
    if args.report:
        cli.generate_report(results)


if __name__ == "__main__":
    main()
