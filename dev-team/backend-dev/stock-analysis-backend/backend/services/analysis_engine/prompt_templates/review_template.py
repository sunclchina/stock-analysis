"""
盘后复盘分析 — 系统提示词模板。

从系统配置的复盘分析模板文件读取提示词。
替换模板中的占位符为真实市场数据。

模板文件：data/templates/A股市场每日复盘分析模板.md
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


# 默认提示词（当模板文件不可用时使用）
FALLBACK_PROMPT = """你是资深股票分析师"青崖复盘"，专注于A股市场盘后复盘分析。

请根据提供的大盘数据、关注股票行情、预警汇总数据，生成完整的复盘分析报告。

报告结构要求：
1. 大盘综述：主要指数表现、成交量、市场情绪
2. 板块轮动：领涨领跌板块、板块持续性
3. 个股分析：关注股票逐一分析
4. 市场异动：涨停跌停、异常波动
5. 明日展望：走势预判、关注重点、风险提示

使用Markdown格式，保持数据支撑的客观分析。"""


def load_review_template() -> str:
    """从模板文件加载复盘分析模板（优先读用户设置的默认模板）"""
    try:
        from backend.api.config_api import resolve_template_path
        path = resolve_template_path("review")
    except Exception:
        path = None
    if not path:
        path = os.path.join("data", "templates", "A股市场每日复盘分析模板.md")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                cut_idx = content.find("# 新数据获取逻辑")
                if cut_idx > 0:
                    content = content[:cut_idx]
                logger.info(f"从 {path} 加载复盘模板 ({len(content)}字符)")
                return content
        except Exception as e:
            logger.warning(f"读取模板文件失败 {path}: {e}")
    logger.warning("复盘模板文件不可用，使用默认提示词")
    return FALLBACK_PROMPT


# 加载模板
REVIEW_SYSTEM_PROMPT = load_review_template()

# 无模板模式：精简结构
REVIEW_SYSTEM_PROMPT_SIMPLE = """你是资深股票分析师"青崖复盘"，专注于A股市场盘后复盘分析。

## 复盘分析报告结构（精简）

### 一、大盘综述
主要指数表现、成交量、市场情绪。

### 二、板块轮动
领涨领跌板块、板块持续性。

### 三、资金流向
北向资金、主力资金、市场情绪。

### 四、市场情绪与行业景气度
涨跌家数、涨停跌停、行业景气度。

### 五、明日展望
走势预判、关注重点、风险提示、操作策略。

## 输出要求
- 使用Markdown格式
- 每个维度都要有数据支撑
- 结论明确
- 不得保留空字段或占位符
- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**
- 如果数据暂时缺失，主动通过联网搜索获取后填充分析
- 总篇幅800-1500字
"""


def build_review_user_prompt(
    date_str: str,
    market_data: str,
    watch_stocks_data: str,
    warning_summary: str,
) -> str:
    """
    构建复盘分析用户输入。
    watch_stocks_data 格式：
    { "input_codes": [...], "market_data": {...} }
    """
    prompt = (
        f"请对 **{date_str}** 的A股市场进行盘后复盘分析。\n\n"
        "请严格按照上面提供的模板结构（九大部分），用以下实时市场数据"
        "填充模板中的每一个占位符（___、【选项A/B/C】等）。\n\n"
        "## 大盘数据\n```json\n" + market_data + "\n```\n\n"
        "## 关注股票列表\n```json\n" + watch_stocks_data + "\n```\n\n"
        "## 今日预警汇总\n```json\n" + warning_summary + "\n```\n\n"
        "要求：\n"
        "- 所有___、【选项/X】等占位符必须用真实数据填充，不得保留任何空字段\n"
        "- 输出完整的分析报告，不得输出模板框架或空白占位符\n"
        "- 保持模板的九大部分结构不变\n"
        "- 第七部分「重点关注股票（个股分析）」规则：\n"
        "  * 如果 input_codes 不为空：必须保留并逐只填充，每只股票独立分析\n"
        "  * 如果 input_codes 为空（即用户没有提供关注股票）：将整个第七部分取消\n"
        "- 关注股票列表中的 input_codes 数组就是用户指定的关注股票\n"
        "- 即使 market_data 中缺少某只股票的行情数据，也应根据股票代码和联网搜索到的信息进行分析\n"
        "- 数据基于联网搜索和已提供的数据，不要编造\n"
        "- **严禁出现「需联网查询」「需确认」「待确认」「数据不足」「需核实」等字样**\n"
        "- 如果数据暂时缺失，主动通过联网搜索获取后填充\n"
        "- 输出使用Markdown格式"
    )
    return prompt
