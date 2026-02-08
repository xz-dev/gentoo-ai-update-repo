# Gentoo ebuild更新提示词

## 概述
这是一个用于AI自动更新Gentoo ebuild文件的提示词模板。

## 使用场景
当需要将软件包更新到上游新版本时使用。

## 提示词模板

```
# Gentoo ebuild 自动更新任务

## 任务信息
- **包名**: {package_name}
- **当前版本**: {current_version}
- **目标版本**: {new_version}
- **上游发布页面**: {source_url}
- **发布日期**: {release_date}

## 当前ebuild内容
```ebuild
{current_ebuild_content}
```

## 上游变化摘要
- 下载URL变化: {download_url_changes}
- 依赖变化: {dependency_changes}
- 其他重要变化: {other_changes}

## 任务步骤

### 1. 分析当前ebuild
识别以下关键部分：
- VERSION/PV变量定义
- SRC_URI配置
- DEPEND/RDEPEND/BDEPEND
- LICENSE和KEYWORDS
- 任何特殊配置或补丁

### 2. 更新版本相关字段
1. **版本号变量**
   - 更新 VERSION 或 PV
   - 如果需要，调整 MY_PV

2. **SRC_URI更新**
   - 更新下载URL为新版本
   - 保持mirrorselect配置
   - 检查checksum变化

3. **依赖检查**
   - 检查新版本是否需要新依赖
   - 移除过时的依赖
   - 调整版本要求

4. **其他调整**
   - 更新HOMEPAGE（如URL变化）
   - 调整LICENSE（如上游许可变化）
   - 更新S（如果目录结构变化）

### 3. 生成新ebuild

请返回完整的更新后ebuild内容：

```ebuild
<完整的ebuild文件内容>
```

### 4. 修改摘要

```markdown
## 修改摘要
- 版本更新: {current_version} → {new_version}
- SRC_URI变更: {src_uri_changes}
- 依赖变更: {dependency_changes}
- 其他调整: {other_changes}
- 需要人工复核: {yes/no}
```

## 质量检查清单
在返回之前，确认：
- [ ] 版本号格式正确
- [ ] SRC_URI格式正确
- [ ] 所有依赖都存在
- [ ] LICENSE有效
- [ ] 没有语法错误
- [ ] 符合Gentoo编码规范
```

## 使用示例

```python
prompt = generate_ebuild_update_prompt(
    package_name="app-editors/neovim",
    current_version="0.9.5",
    new_version="0.10.0",
    source_url="https://github.com/neovim/neovim/releases",
    release_date="2024-06-11",
    current_ebuild_content=read_ebuild_content()
)
```
