"""
批量分析 — 系统提示词模板。

从系统配置的批量股票分析模板文件读取提示词。
模板文件：data/templates/A股个股_批量股票分析模板.md
"""

import os
import logging

logger = logging.getLogger(__name__)

# 无模板模式：精简结构
BATCH_ANALYSIS_SYSTEM_PROMPT_SIMPLE = """你是资深股票分析师"青崖"，专注于个股批量对比分析。

## 批量分析报告结构（五大部分）

### 一、整体概览
分析股票总数、整体市场环境判断、这批股票共同特征。

### 二、逐只分析
每只股票独立分析，包含：价格、趋势判断、综合评分、预警状态、核心判断、操作建议。

### 三、横向对比
综合评分排序、按风险等级分组、按行业/风格分组。

### 四、优选推荐
推荐买入（前3只）、推荐关注（中等评级）、建议回避（高风险）。

### 五、组合建议
- 逐只分析简洁明了
- 不得保留空字段或占位符
- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**
- 如果数据暂时缺失，主动通过联网搜索获取后填充分析
- 总篇幅1500-2500字
"""

FALLBACK_PROMPT = """你是资深股票分析师"青崖"，专注于个股批量对比分析。

## 批量分析报告结构

### 一、整体概览
### 二、逐只分析
### 三、横向对比
### 四、优选推荐
### 五、组合建议
"""


def load_batch_template() -> str:
    """从模板文件加载批量分析模板（优先读用户设置的默认模板）"""
    try:
        from backend.api.config_api import resolve_template_path
        path = resolve_template_path("batch")
    except Exception:
        path = None
    if not path:
        path = os.path.join("data", "templates", "A股个股_批量股票分析模板.md")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"从 {path} 加载批量分析模板 ({len(content)}字符)")
                return content
        except Exception as e:
            logger.warning(f"读取批量模板文件失败 {path}: {e}")
    logger.warning("批量分析模板文件不可用，使用默认提示词")
    return FALLBACK_PROMPT


BATCH_ANALYSIS_SYSTEM_PROMPT = load_batch_template()


def build_batch_analysis_user_prompt(
    stocks_data: str,
    warning_data: str,
) -> str:
    """构建批量分析用户输入。"""
    return f"""请对以下股票列表进行批量对比分析。

请严格按上面模板的结构和格式，用以下数据填充分析内容。模板中的"模型自动"类说明表示该部分由你完成，请直接填充真实分析结果，切勿保留"模型自动填充"等字眼。

## 股票数据
```json
{stocks_data}
```

## 预警汇总
```json
{warning_data}
```

要求：
- 不得保留任何空的占位符
- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**
- 如果数据暂时缺失，主动通过联网搜索获取后填充分析
- 输出使用Markdown格式"""
