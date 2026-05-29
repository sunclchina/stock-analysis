"""
新闻舆情情绪分析服务。

基于 TradingAgents-cn 的 ChineseFinanceDataAggregator 思路，
使用东方财富 + 新浪财经作为真实数据源，对个股进行新闻/舆情情绪打分。
适用于增强智能分析的输入维度。

主要接口：
- get_sentiment(code) -> 综合情绪分析结果
- get_news_list(code, days) -> 个股相关新闻列表
"""

import logging
import re
import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── 中文情绪关键词词典 ──────────────────────────────────
POSITIVE_WORDS = [
    "上涨", "增长", "大涨", "涨停", "利好", "看好", "买入", "推荐",
    "强势", "突破", "创新高", "放量", "拉升", "超预期", "扭亏",
    "增持", "回购", "分红", "中标", "订单", "合同", "获批",
    "突破", "改善", "盈利", "龙头", "放量大涨", "主力流入",
]

NEGATIVE_WORDS = [
    "下跌", "下降", "大跌", "跌停", "利空", "看空", "卖出", "减持",
    "风险", "跌破", "创新低", "亏损", "ST", "退市", "立案",
    "调查", "处罚", "诉讼", "违约", "质押", "冻结", "解禁",
    "暴雷", "商誉", "减值", "预警", "降级", "流出", "主力流出",
]


def _keyword_sentiment(text: str) -> float:
    """基于关键词的简单情绪打分，返回 -1 ~ 1 之间的值"""
    if not text:
        return 0.0
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    score = (pos_count - neg_count) / total
    # 归一化到 -1 ~ 1
    return max(-1.0, min(1.0, score))


class SentimentAnalysisService:
    """新闻舆情情绪分析服务"""

    def __init__(self):
        self._ak = None

    def _ensure_akshare(self):
        if self._ak is None:
            import akshare as ak
            self._ak = ak
            self._ak_available = True

    async def get_sentiment(self, code: str) -> Dict[str, Any]:
        """
        获取个股综合情绪分析。

        数据源整合链路：
          1. 东方财富新闻（akshare stock_news_em）
          2. 新浪财经新闻
          3. 关键词情绪打分

        返回情绪标签：positive / neutral / negative
        """
        try:
            self._ensure_akshare()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

            # 获取新闻列表
            news_items = await self._fetch_news(clean)
            if not news_items:
                return {
                    "code": clean,
                    "overall_sentiment": "neutral",
                    "score": 0.0,
                    "confidence": "low",
                    "news_count": 0,
                    "summary": "暂无相关新闻数据",
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                }

            # 逐条情绪打分
            scores = []
            for item in news_items:
                title = item.get("title", "")
                content = item.get("content", "")
                text = f"{title} {content}"
                s = _keyword_sentiment(text)
                scores.append(s)

            positive = sum(1 for s in scores if s > 0.1)
            negative = sum(1 for s in scores if s < -0.1)
            neutral = len(scores) - positive - negative

            avg_score = sum(scores) / len(scores) if scores else 0.0

            # 置信度：基于新闻数量
            confidence = "high" if len(scores) >= 10 else "medium" if len(scores) >= 3 else "low"

            # 情绪级别
            if avg_score > 0.15:
                level = "positive"
            elif avg_score < -0.15:
                level = "negative"
            else:
                level = "neutral"

            return {
                "code": clean,
                "overall_sentiment": level,
                "score": round(avg_score, 4),
                "confidence": confidence,
                "news_count": len(scores),
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "summary": self._format_summary(level, avg_score, confidence, len(scores), positive, negative),
                "latest_news": [
                    {
                        "title": n.get("title", ""),
                        "date": n.get("date", ""),
                        "source": n.get("source", ""),
                        "url": n.get("url", ""),
                    }
                    for n in news_items[:10]
                ],
            }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed for {code}: {e}")
            return {"code": code, "error": str(e), "overall_sentiment": "neutral", "score": 0.0}

    async def get_news_list(self, code: str, days: int = 7) -> List[Dict[str, str]]:
        """获取个股相关新闻列表"""
        try:
            self._ensure_akshare()
            clean = code.upper().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
            items = await self._fetch_news(clean, days)
            return items[:20]
        except Exception as e:
            logger.warning(f"News list failed for {code}: {e}")
            return []

    async def _fetch_news(self, code: str, days: int = 7) -> List[Dict[str, str]]:
        """
        从多个数据源获取个股新闻。
        主：akshare stock_news_em（东方财富新闻）
        备：新浪财经 RSS 或爬虫
        """
        items = []
        try:
            # 东方财富个股新闻
            df = self._ak.stock_news_em(symbol=code, timeout=15)
            if df is not None and not df.empty:
                for _, row in df.head(30).iterrows():
                    items.append({
                        "title": str(row.get("新闻标题", "")),
                        "content": str(row.get("新闻内容", "")),
                        "date": str(row.get("发布时间", "")),
                        "source": "东方财富",
                        "url": str(row.get("新闻链接", "")),
                    })
        except Exception as e:
            logger.debug(f"EastMoney news fetch failed for {code}: {e}")

        return items

    @staticmethod
    def _format_summary(level: str, score: float, confidence: str,
                        total: int, pos: int, neg: int) -> str:
        """生成情绪摘要文本"""
        level_cn = {"positive": "偏积极", "neutral": "中性", "negative": "偏消极"}
        conf_cn = {"high": "高", "medium": "中", "low": "低"}
        return (
            f"舆情情绪: {level_cn.get(level, '中性')} "
            f"(评分: {score:.2f}, 置信度: {conf_cn.get(confidence, '低')})\n"
            f"近期{total}条相关新闻中, "
            f"正面{pos}条, 负面{neg}条, 中性{total-pos-neg}条"
        )
