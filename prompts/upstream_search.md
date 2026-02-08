# Gentoo软件包上游版本搜索提示词

## 概述
这是一个用于AI驱动的上游版本检测的通用提示词模板。

## 使用场景
当需要检查Gentoo软件包是否有上游新版本时使用。

## 提示词模板

```
# Gentoo软件包上游版本搜索任务

## 任务背景
你是一个专业的Gentoo Linux软件包维护助手。任务是找到指定软件包的最新上游版本。

## 目标软件包信息
- **包名**: {package_name}
- **分类**: {package_type}
- **Gentoo当前版本**: {current_version}

## 已知的上游信息
- **可能的发布页面**: {possible_urls}
- **软件类型**: {software_type}

## 搜索策略

### 第一步：定位上游源
1. 搜索 "{package_name} official website"
2. 搜索 "{package_name} latest stable release"
3. 检查GitHub/GitLab releases

### 第二步：提取版本信息
1. 找到最新的稳定版本号
2. 确认发布日期
3. 获取下载链接

## 输出格式

请返回JSON格式的结果：

```json
{
    "package": "{package_name}",
    "current_version": "{current_version}",
    "latest_version": "最新版本号（去除v前缀）",
    "release_date": "YYYY-MM-DD",
    "source_url": "官方发布页面URL",
    "download_url": "下载链接模板",
    "confidence": 0.95,
    "search_steps": [
        "步骤1: 搜索了...",
        "步骤2: 在...找到了版本"
    ],
    "notes": "备注信息"
}
```

## 重要规则
1. 版本号以"v"开头的一定要去掉
2. 只选择stable稳定版
3. confidence反映你的信心度
4. source_url必须提供
5. 找不到时要诚说明
```

## 使用示例

### 检查 neovim
```python
prompt = generate_upstream_search_prompt(
    package_name="app-editors/neovim",
    package_type="编辑器",
    current_version="0.9.5",
    software_type="终端编辑器"
)
```

### 检查 ripgrep
```python
prompt = generate_upstream_search_prompt(
    package_name="sys-apps/ripgrep",
    package_type="系统工具",
    current_version="14.0.0",
    software_type="搜索工具"
)
```
