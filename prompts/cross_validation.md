# 多源交叉验证提示词

## 概述
这是一个用于AI验证版本检测结果的提示词模板。

## 使用场景
当需要验证从多个源获取的版本信息是否一致时使用。

## 提示词模板

```
# 版本交叉验证任务

## 任务背景
你是一个软件版本验证专家。任务是验证从多个源获取的版本信息。

## 待验证的信息
- **包名**: {package_name}
- **Gentoo当前版本**: {current_version}
- **AI检测的最新版本**: {ai_detected_version}
- **AI置信度**: {ai_confidence}

## 验证源数据

### 源1: {source1_name}
- **版本**: {source1_version}
- **URL**: {source1_url}
- **可信度**: {source1_reliability}

### 源2: {source2_name}
- **版本**: {source2_version}
- **URL**: {source2_url}
- **可信度**: {source2_reliability}

### 源3: {source3_name}
- **版本**: {source3_version}
- **URL**: {source3_url}
- **可信度**: {source3_reliability}

## 验证任务

### 1. 版本一致性分析
- 比较各源的版本号
- 识别任何不一致
- 评估版本差异的严重性

### 2. 可信度评估
- 各源的可信度评分
- 版本信息的时效性
- 潜在的风险因素

### 3. 最终结论
- 最终确定的版本号
- 综合置信度
- 是否需要人工复核

## 输出格式

```json
{
    "package": "{package_name}",
    "verified_version": "最终确认的版本号",
    "confidence": 0.92,
    "sources_agree": true/false,
    "consensus_details": {
        "agreement": "所有源都确认此版本",
        "disagreement": "源1和源2确认，但源3不同"
    },
    "risk_assessment": {
        "level": "low/medium/high",
        "factors": ["因素1", "因素2"]
    },
    "recommendation": "建议：更新 / 等待 / 人工复核",
    "notes": "其他备注"
}
```

## 验证原则
1. **多数原则**: 多数源确认的版本更可信
2. **时效性**: 优先相信最新更新的源
3. **官方源**: 官方发布页通常最可靠
4. **社区源**: Arch/Nix等滚动发行版通常较新
```

## 使用示例

```python
prompt = generate_cross_validation_prompt(
    package_name="app-editors/neovim",
    current_version="0.9.5",
    ai_detected_version="0.10.0",
    ai_confidence=0.85,
    sources={
        "github": {"version": "0.10.0", "url": "...", "reliability": 0.95},
        "arch": {"version": "0.10.0-1", "url": "...", "reliability": 0.90},
        "pypi": None
    }
)
```
