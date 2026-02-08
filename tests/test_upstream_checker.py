#!/usr/bin/env python3
"""
Gentoo AI 包维护系统 - 测试脚本

测试功能:
1. 上游版本检测
2. 交叉验证
3. ebuild更新（如果需要）

作者: AI Gentoo Maintainer
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.version_checker import AIUpstreamChecker, VersionCheckResult
from core.version_validator import MultiSourceValidator
from core.ebuild_updater import EbuildUpdater


def test_version_checker():
    """测试版本检查器"""
    print("\n" + "=" * 70)
    print("测试 1: 版本检查器")
    print("=" * 70)

    checker = AIUpstreamChecker()

    # 测试用例
    test_packages = [
        (
            "app-editors/neovim",
            "/var/db/repos/gentoo/app-editors/neovim/neovim-0.11.5.ebuild",
        ),
        (
            "sys-apps/ripgrep",
            "/var/db/repos/gentoo/sys-apps/ripgrep/ripgrep-15.1.0.ebuild",
        ),
    ]

    results = []
    for package, ebuild_path in test_packages:
        print(f"\n检查包: {package}")
        print(f"ebuild路径: {ebuild_path}")

        try:
            result = checker.get_upstream_info(package, ebuild_path)

            print(f"\n结果:")
            print(f"  当前版本: {result.current_version}")
            print(f"  最新版本: {result.latest_version}")
            print(f"  置信度: {result.confidence:.0%}")
            print(f"  需要更新: {'是' if result.needs_update else '否'}")
            print(f"  发布页面: {result.source_url or '未找到'}")

            if result.raw_ai_response:
                print(f"\n  AI响应长度: {len(result.raw_ai_response)} 字符")

            results.append(
                {"package": package, "success": True, "result": result.__dict__}
            )

        except Exception as e:
            print(f"\n错误: {e}")
            results.append({"package": package, "success": False, "error": str(e)})

    return results


def test_version_validator():
    """测试版本验证器"""
    print("\n" + "=" * 70)
    print("测试 2: 版本验证器")
    print("=" * 70)

    import asyncio

    validator = MultiSourceValidator()

    # 测试用例
    test_cases = [
        {
            "package": "app-editors/neovim",
            "current_version": "0.11.5",
            "latest_version": "0.11.6",
            "confidence": 0.85,
            "source_url": "https://github.com/neovim/neovim/releases",
        }
    ]

    validation_results = []
    for test_case in test_cases:
        print(f"\n验证包: {test_case['package']}")
        print(f"  当前版本: {test_case['current_version']}")
        print(f"  检测版本: {test_case['latest_version']}")

        try:
            result = asyncio.run(
                validator.validate_version(test_case["package"], test_case)
            )

            print(f"\n验证结果:")
            print(f"  最终置信度: {result['final_confidence']:.0%}")
            print(f"  验证通过: {'是' if result['is_verified'] else '否'}")
            print(f"  需要人工复核: {'是' if result['needs_manual_review'] else '否'}")

            validation_results.append(
                {"package": test_case["package"], "success": True, "result": result}
            )

        except Exception as e:
            print(f"\n错误: {e}")
            validation_results.append(
                {"package": test_case["package"], "success": False, "error": str(e)}
            )

    return validation_results


def test_ebuild_updater():
    """测试ebuild更新器"""
    print("\n" + "=" * 70)
    print("测试 3: ebuild更新器")
    print("=" * 70)

    updater = EbuildUpdater()

    # 测试用例 - 只测试不需要实际更新的场景
    test_cases = [
        {
            "package": "app-editors/neovim",
            "current_version": "0.11.5",
            "new_version": "0.11.5",  # 相同版本，不会有实际更新
            "upstream_info": {
                "source_url": "https://github.com/neovim/neovim/releases",
                "download_url": "https://github.com/neovim/neovim/releases/download/v${PV}/nvim-linux64.tar.gz",
                "release_date": "2024-12-01",
            },
        }
    ]

    update_results = []
    for test_case in test_cases:
        print(f"\n测试包: {test_case['package']}")
        print(f"  当前版本: {test_case['current_version']}")
        print(f"  新版本: {test_case['new_version']}")

        try:
            result = updater.update_ebuild(**test_case)

            print(f"\n更新结果:")
            print(f"  成功: {'是' if result.success else '否'}")
            print(f"  ebuild路径: {result.ebuild_path or '未创建'}")
            print(f"  需要人工复核: {'是' if result.needs_manual_review else '否'}")

            if result.errors:
                print(f"  错误:")
                for error in result.errors:
                    print(f"    - {error}")

            update_results.append(
                {
                    "package": test_case["package"],
                    "success": True,
                    "result": result.__dict__,
                }
            )

        except Exception as e:
            print(f"\n错误: {e}")
            update_results.append(
                {"package": test_case["package"], "success": False, "error": str(e)}
            )

    return update_results


def generate_test_report(results: Dict):
    """生成测试报告"""
    print("\n" + "=" * 70)
    print("测试报告")
    print("=" * 70)

    report = {
        "timestamp": str(__import__("datetime").datetime.now()),
        "tests": {
            "version_checker": {
                "total": len(results.get("version_checker", [])),
                "passed": sum(
                    1 for r in results.get("version_checker", []) if r.get("success")
                ),
                "failed": sum(
                    1
                    for r in results.get("version_checker", [])
                    if not r.get("success")
                ),
            },
            "version_validator": {
                "total": len(results.get("version_validator", [])),
                "passed": sum(
                    1 for r in results.get("version_validator", []) if r.get("success")
                ),
                "failed": sum(
                    1
                    for r in results.get("version_validator", [])
                    if not r.get("success")
                ),
            },
            "ebuild_updater": {
                "total": len(results.get("ebuild_updater", [])),
                "passed": sum(
                    1 for r in results.get("ebuild_updater", []) if r.get("success")
                ),
                "failed": sum(
                    1 for r in results.get("ebuild_updater", []) if not r.get("success")
                ),
            },
        },
    }

    print(f"\n版本检查器:")
    print(f"  总数: {report['tests']['version_checker']['total']}")
    print(f"  通过: {report['tests']['version_checker']['passed']}")
    print(f"  失败: {report['tests']['version_checker']['failed']}")

    print(f"\n版本验证器:")
    print(f"  总数: {report['tests']['version_validator']['total']}")
    print(f"  通过: {report['tests']['version_validator']['passed']}")
    print(f"  失败: {report['tests']['version_validator']['failed']}")

    print(f"\nebuild更新器:")
    print(f"  总数: {report['tests']['ebuild_updater']['total']}")
    print(f"  通过: {report['tests']['ebuild_updater']['passed']}")
    print(f"  失败: {report['tests']['ebuild_updater']['failed']}")

    # 保存报告
    report_file = (
        Path(__file__).parent.parent
        / "logs"
        / f"test_report_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n报告已保存: {report_file}")

    return report


def main():
    """主测试函数"""

    print("=" * 70)
    print("Gentoo AI 包维护系统 - 测试套件")
    print("=" * 70)
    print(f"测试时间: {__import__('datetime').datetime.now()}")
    print(f"Python版本: {sys.version}")
    print("=" * 70)

    results = {}

    # 运行测试
    print("\n开始测试...\n")

    try:
        results["version_checker"] = test_version_checker()
    except Exception as e:
        print(f"\n版本检查器测试出错: {e}")
        results["version_checker"] = [{"success": False, "error": str(e)}]

    try:
        results["version_validator"] = test_version_validator()
    except Exception as e:
        print(f"\n版本验证器测试出错: {e}")
        results["version_validator"] = [{"success": False, "error": str(e)}]

    try:
        results["ebuild_updater"] = test_ebuild_updater()
    except Exception as e:
        print(f"\nebuild更新器测试出错: {e}")
        results["ebuild_updater"] = [{"success": False, "error": str(e)}]

    # 生成报告
    report = generate_test_report(results)

    # 总结
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)

    # 计算总数
    total_passed = 0
    total_tests = 0
    for test_name, test_data in report["tests"].items():
        total_passed += test_data["passed"]
        total_tests += test_data["total"]

    print(
        f"\n总通过率: {total_passed}/{total_tests} ({100 * total_passed / total_tests:.0f}%)"
    )


if __name__ == "__main__":
    main()
