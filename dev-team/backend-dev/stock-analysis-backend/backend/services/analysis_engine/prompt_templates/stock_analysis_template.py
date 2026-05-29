"""
个股分析 — 系统提示词模板。

从系统配置的个股分析模板文件读取提示词。
模板文件：data/templates/A股个股_批量股票分析模板.md
"""

import os
import logging

logger = logging.getLogger(__name__)

# 无模板模式：精简的五大部分结构
STOCK_ANALYSIS_SYSTEM_PROMPT_SIMPLE = """你是资深股票分析师"青崖"，专注于A股个股深度分析。

## 个股分析报告结构（五大部分）

### 一、股票概览
股票名称、代码、当前价格、所属行业、市值规模、今日涨跌幅、成交量。

### 二、技术面分析
趋势分析（均线排列）、关键指标（RSI/MACD/KDJ/BOLL）、量能分析。

### 三、基本面概况
PE/PB/ROE、营收/利润增速、资产负债率、估值判断。

### 四、预警信号
各模块预警状态、主要风险因素、异动信号。

### 五、综合结论与建议
综合评分、操作建议、支撑位/压力位、风险提示。

## 输出要求
- 使用Markdown格式
- 每个分析维度都要有数据支撑
- 结论明确
- 不得保留空字段或占位符
- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**
- 如果数据暂时缺失，主动通过联网搜索获取后填充分析
- 总篇幅800-1500字
"""


# 默认提示词（当模板文件不可用时使用）
FALLBACK_PROMPT = """你是资深股票分析师"青崖"，专注于A股个股深度分析。

## 个股分析报告结构

### 一、股票概览
### 二、技术面分析
### 三、基本面概况
### 四、预警信号
### 五、综合结论与建议
"""


def load_stock_template() -> str:
    """从模板文件加载个股分析模板（优先读用户设置的默认模板）"""
    try:
        from backend.api.config_api import resolve_template_path
        path = resolve_template_path("stock")
    except Exception:
        path = None
    if not path:
        path = os.path.join("data", "templates", "A股个股_批量股票分析模板.md")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"从 {path} 加载个股分析模板 ({len(content)}字符)")
                return content
        except Exception as e:
            logger.warning(f"读取个股模板文件失败 {path}: {e}")
    logger.warning("个股分析模板文件不可用，使用默认提示词")
    return FALLBACK_PROMPT


STOCK_ANALYSIS_SYSTEM_PROMPT = load_stock_template()


def build_stock_analysis_user_prompt(
    code: str,
    name: str,
    market_data: str,
    kline_data: str,
    finance_data: str,
) -> str:
    """构建个股分析用户输入。"""
    return f"""请对以下A股个股进行深度分析。

股票代码：{code}
股票名称：{name}

请严格按照上面提供的模板结构，用以下真实数据填充分析内容。

## 行情数据
```json
{market_data}
```

## K线数据
```json
{kline_data}
```

## 财务数据
```json
{finance_data}
```

要求：
- 所有占位符必须用真实数据填充
- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**
- 如果数据暂时缺失，主动通过联网搜索获取后填充分析
- 输出使用Markdown格式
"""
