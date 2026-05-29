"""
突发事件检测模块。
从巨潮资讯网（cninfo.com.cn）按关键词搜索公告，识别 9 类负面事件。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# 9 类事件搜索配置
EVENT_QUERIES = [
    {"id": "fraud", "label": "财务造假被立案", "keyword": "财务造假", "ann_type": ""},
    {"id": "audit_opinion", "label": "财报被出具否定/无法表示意见", "keyword": "无法表示意见", "ann_type": ""},
    {"id": "audit_opinion2", "label": "财报被出具否定/无法表示意见", "keyword": "否定意见", "ann_type": ""},
    {"id": "debt_default", "label": "债务违约/展期", "keyword": "债务违约", "ann_type": ""},
    {"id": "debt_overdue", "label": "债务违约/展期", "keyword": "逾期", "ann_type": ""},
    {"id": "debt_extend", "label": "债务违约/展期", "keyword": "展期", "ann_type": ""},
    {"id": "pledge_high", "label": "质押比例>90%且股价接近平仓线", "keyword": "质押比例 90%", "ann_type": ""},
    {"id": "pledge_margin", "label": "质押比例>90%且股价接近平仓线", "keyword": "平仓线", "ann_type": ""},
    {"id": "sanction", "label": "被公开谴责或行政处罚", "keyword": "行政处罚", "ann_type": ""},
    {"id": "censure", "label": "被公开谴责或行政处罚", "keyword": "公开谴责", "ann_type": ""},
    {"id": "inquire", "label": "收到监管问询函未回复", "keyword": "问询函未回复", "ann_type": ""},
    {"id": "revenue_decline", "label": "营业收入同比增速<-20%", "keyword": "营业收入同比下降20%", "ann_type": ""},
    {"id": "profit_negative", "label": "扣非净利润/净利润增速为负", "keyword": "扣非净利润同比下降", "ann_type": ""},
    {"id": "accounting_error", "label": "发布前期会计差错更正公告", "keyword": "前期会计差错更正", "ann_type": ""},
]

# 合并相同标签的事件（去重标签）
EVENT_LABELS = [
    ("财务造假被立案", ["fraud"]),
    ("财报被出具否定/无法表示意见", ["audit_opinion", "audit_opinion2"]),
    ("债务违约/展期", ["debt_default", "debt_overdue", "debt_extend"]),
    ("质押比例>90%且股价接近平仓线", ["pledge_high", "pledge_margin"]),
    ("被公开谴责或行政处罚", ["sanction", "censure"]),
    ("收到监管问询函未回复", ["inquire"]),
    ("营业收入同比增速<-20%", ["revenue_decline"]),
    ("扣非净利润/净利润增速为负", ["profit_negative"]),
    ("发布前期会计差错更正公告", ["accounting_error"]),
]


def _query_cninfo(searchkey: str) -> List[Dict]:
    """查询巨潮资讯网公告"""
    import httpx
    from datetime import datetime as _cn_dt
    
    url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
    }
    
    # 搜索近一年
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    data = {
        "pageNum": "1",
        "pageSize": "30",
        "column": "szse",
        "tabName": "fulltext",
        "plate": "sz",
        "stock": "",
        "searchkey": searchkey,
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date}~{end_date}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }
    
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, data=data, headers=headers)
            result = resp.json()
            anns = result.get("announcements") or []
            def _parse_ann(ann):
                ts = ann.get("announcementTime", 0)
                date_str = _cn_dt.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else ""
                return {
                    "code": ann.get("secCode", ""),
                    "name": ann.get("secName", ""),
                    "title": ann.get("announcementTitle", "").replace("<em>", "").replace("</em>", ""),
                    "date": date_str,
                    "url": f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={ann.get('announcementId', '')}",
                }
            return [_parse_ann(ann) for ann in anns if ann.get("secCode")]
    except Exception as e:
        logger.warning(f"CNINFO查询失败 [{searchkey}]: {e}")
        return []


def fetch_all_events() -> Dict[str, Any]:
    """获取所有突发事件股票"""
    all_stocks = {}  # code -> {code, name, events: [{label, title, date}]}
    query_stats = {}
    
    for eq in EVENT_QUERIES:
        results = _query_cninfo(eq["keyword"])
        query_stats[eq["id"]] = {"keyword": eq["keyword"], "results": len(results)}
        
        for item in results:
            code = item["code"]
            if code not in all_stocks:
                all_stocks[code] = {
                    "code": code,
                    "name": item["name"],
                    "events": [],
                    "latest_date": "",
                }
            # 检查是否已存在相同事件标签
            label = eq["label"]
            existing_labels = [e["label"] for e in all_stocks[code]["events"]]
            if label not in existing_labels:
                all_stocks[code]["events"].append({
                    "label": label,
                    "keyword": eq["keyword"],
                    "title": item["title"],
                    "date": item["date"],
                    "url": item["url"],
                })
                # 更新最新日期
                if item["date"] > all_stocks[code]["latest_date"]:
                    all_stocks[code]["latest_date"] = item["date"]
    
    # 统一标签（合并）
    for code, stock in all_stocks.items():
        merged = {}
        for e in stock["events"]:
            label = e["label"]
            if label not in merged:
                merged[label] = e
            else:
                # 保留更近的日期
                if e["date"] > merged[label]["date"]:
                    merged[label] = e
        stock["events"] = list(merged.values())
    
    items = sorted(all_stocks.values(), key=lambda x: x["latest_date"], reverse=True)
    
    return {
        "items": items,
        "count": len(items),
        "query_stats": query_stats,
        "generated_at": datetime.now().isoformat(),
    }
