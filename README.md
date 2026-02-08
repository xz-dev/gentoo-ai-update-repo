# Gentoo AI 软件包维护系统

## 概述

这是一个AI驱动的Gentoo软件包自动维护系统，使用k2.5 free模型自动：
1. 检测上游软件版本
2. 交叉验证版本信息
3. 自动更新ebuild文件
4. 执行质量检查和自动修复

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   版本监控触发层                         │
│              （手动触发 / 定时任务 / webhook）           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│               AI版本检查协调层                           │
│   使用k2.5 free模型通过Perplexity/Firecrawl搜索          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                 多源交叉验证层                            │
│   GitHub Releases / Arch Linux / PyPI / NPM             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  ebuild更新执行层                        │
│   AI生成更新提示词 → repoman检查 → 自动修复               │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
gentoo-ai-update-repo/
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── version_checker.py   # AI驱动的上游版本检查器
│   ├── version_validator.py # 多源交叉验证
│   └── ebuild_updater.py    # ebuild更新器
├── prompts/                  # AI提示词模板
│   ├── upstream_search.md   # 上游版本搜索提示词
│   ├── ebuild_update.md     # ebuild更新提示词
│   └── cross_validation.md  # 交叉验证提示词
├── scripts/                  # 执行脚本
│   ├── ai_upstream_checker.sh  # Bash前端
│   └── ai_upstream_checker.py  # Python核心
├── tests/                    # 测试文件
│   └── test_upstream_checker.py
├── config/                   # 配置文件
│   └── settings.json
├── data/                     # 数据文件
│   └── packages_to_monitor.txt
├── logs/                     # 日志目录
├── backups/                  # 备份目录
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# 确保Python 3.8+
python3 --version

# 安装依赖（如果需要）
pip3 install -r requirements.txt
```

### 2. 配置监控包列表

编辑 `data/packages_to_monitor.txt`，添加要监控的包：

```
# 格式: category/package_name
app-editors/neovim
sys-apps/htop
dev-vcs/git
```

### 3. 运行检查

```bash
# 检查所有配置的包
./scripts/ai_upstream_checker.sh

# 检查单个包
./scripts/ai_upstream_checker.sh app-editors/neovim

# 生成报告
./scripts/ai_upstream_checker.sh --report

# 显示详细输出
./scripts/ai_upstream_checker.sh --verbose

# 清除缓存后重新检查
./scripts/ai_upstream_checker.sh --cache-clear
```

### 4. 使用Python脚本

```bash
# 批量检查
python3 scripts/ai_upstream_checker.py

# 单包检查
python3 scripts/ai_upstream_checker.py app-editors/neovim

# 生成报告
python3 scripts/ai_upstream_checker.py --report
```

## 配置说明

编辑 `config/settings.json` 自定义行为：

```json
{
    "system": {
        "model": "k2.5-free",        // AI模型
        "parallel_workers": 3,         // 并行工作数
        "cache_ttl_hours": 24,         // 缓存有效期
        "confidence_threshold": 0.7    // 置信度阈值
    },
    "validation": {
        "enabled": true,              // 是否启用验证
        "sources": {
            "github": {"enabled": true, "weight": 0.4},
            "arch_linux": {"enabled": true, "weight": 0.3}
        }
    }
}
```

## AI提示词

系统使用预定义的提示词模板，位于 `prompts/` 目录：

- `upstream_search.md`: 上游版本搜索
- `ebuild_update.md`: ebuild更新
- `cross_validation.md`: 多源交叉验证

## 测试

```bash
# 运行测试套件
python3 tests/test_upstream_checker.py

# 测试结果保存在 logs/ 目录
```

## 工作流程

1. **版本检测**
   - AI搜索上游最新版本
   - 尝试多个搜索策略
   - 提取版本号和发布信息

2. **交叉验证**
   - 检查GitHub Releases
   - 对比Arch Linux版本
   - 计算综合置信度

3. **ebuild更新**
   - 分析当前ebuild
   - 更新版本号和SRC_URI
   - 调整依赖（如果需要）

4. **质量检查**
   - 运行repoman full
   - 预演安装过程
   - 自动修复常见问题

## 注意事项

1. **API限制**: 系统使用k2.5 free模型，注意API调用限制
2. **缓存机制**: 相同检查24小时内不会重复
3. **人工复核**: 置信度低于0.7的结果需要人工确认
4. **备份**: 更新前会自动备份原ebuild

## 故障排除

### 检查失败
```bash
# 清除缓存后重试
./scripts/ai_upstream_checker.sh --cache-clear
```

### 查看详细日志
```bash
# 使用verbose模式
./scripts/ai_upstream_checker.sh --verbose

# 查看日志目录
ls -la logs/
```

## 贡献

欢迎贡献代码或建议！请：
1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 许可证

MIT License

## 作者

AI Gentoo Maintainer
