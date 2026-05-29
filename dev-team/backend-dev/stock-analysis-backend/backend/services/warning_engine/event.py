"""
M03 预警计算引擎 — 突发预警模块（按设计文档完全重写）

规则来源：6.智能预警模块.md §3.6 突发预警

加权计分：
· 重大负面事件：3分
· 一般负面事件（高权重）：1.5分（质押60-80%、债务逾期未违约、高管集体减持等）
· 一般负面事件（低权重）：0.5分（问询函、信披考评D等）

分级：
· 🟢 安全：总分 = 0
· 🟡 关注：0 < 总分 < 2
· 🔴 风险：2 ≤ 总分 < 4
· ⚫ 规避：总分 ≥ 4 或 任意硬规避项

硬规避项（直接⚫）：
· 财务造假被立案且证据确凿
· 财报被出具否定/无法表示意见
· 债务违约/展期
· 质押比例>90%且股价接近平仓线
· 被公开谴责或行政处罚（近1年）

更新频率：每日开盘前从数据库加载一次，交易期间不实时变化。
"""

from typing import Optional, Dict, Any, List
import json
import logging

from backend.services.warning_engine.price import WarningResult

logger = logging.getLogger(__name__)

# ─── 事件定义 ─────────────────────────────────────

# 重大负面事件（3分）
MAJOR_EVENTS = {
    "major_restructuring_fail": "重大资产重组失败",
    "major_lawsuit_loss": "重大诉讼败诉",
    "core_business_shutdown": "核心业务停摆",
    "delisting_warning": "退市风险警示",
}

# 一般负面事件-高权重（1.5分）
HIGH_WEIGHT_EVENTS = {
    "audit_qualified_opinion": "财报保留意见",
    "pledge_60_80": "大股东质押比例60%-80%",
    "debt_overdue_no_default": "债务逾期未违约",
    "executive_mass_sell": "高管集体减持（≥3人）",
    "major_contract_loss": "重大合同违约",
    "major_asset_impairment": "重大资产减值",
}

# 一般负面事件-低权重（0.5分）
LOW_WEIGHT_EVENTS = {
    "inquiry_letter": "收到监管问询函未回复",
    "info_disclosure_d": "信披考评D",
    "pledge_40_60": "大股东质押比例40%-60%",
    "sell_1_3_pct": "6个月内减持1%-3%",
    "board_resignation": "独立董事辞职",
    "profit_warning": "业绩预告变脸",
}

# 硬规避项
HARD_AVOID_EVENTS = {
    "fraud_investigation": "财务造假被立案且证据确凿",
    "audit_negative_opinion": "财报被出具否定/无法表示意见",
    "debt_default": "债务违约/展期",
    "pledge_over_90": "质押比例>90%且股价接近平仓线",
    "public_censure": "被公开谴责或行政处罚（近1年）",
}

ALL_EVENTS = {}
ALL_EVENTS.update(MAJOR_EVENTS)
ALL_EVENTS.update(HIGH_WEIGHT_EVENTS)
ALL_EVENTS.update(LOW_WEIGHT_EVENTS)
ALL_EVENTS.update(HARD_AVOID_EVENTS)

# 事件权重映射
EVENT_WEIGHTS = {}
for k in MAJOR_EVENTS:
    EVENT_WEIGHTS[k] = 3.0
for k in HIGH_WEIGHT_EVENTS:
    EVENT_WEIGHTS[k] = 1.5
for k in LOW_WEIGHT_EVENTS:
    EVENT_WEIGHTS[k] = 0.5
for k in HARD_AVOID_EVENTS:
    EVENT_WEIGHTS[k] = 999  # 硬规避

# 颜色映射
COLOR_MAP = {
    0: "green",
    1: "yellow",
    2: "red",
    3: "black",
}


def score_to_color(total_score: float, has_hard_avoid: bool) -> str:
    """按设计文档分级规则映射颜色"""
    if has_hard_avoid or total_score >= 4:
        return "black"
    elif total_score >= 2:
        return "red"
    elif total_score > 0:
        return "yellow"
    else:
        return "green"


def score_to_label(total_score: float, has_hard_avoid: bool) -> str:
    if has_hard_avoid or total_score >= 4:
        return "规避"
    elif total_score >= 2:
        return "风险"
    elif total_score > 0:
        return "关注"
    else:
        return "安全"


def get_stock_events(code: str) -> Dict[str, Any]:
    """
    从数据库或静态数据源加载指定股票的突发事件列表。
    
    每日开盘前加载一次，交易日期间不实时变化。
    返回格式：{"events": [{"key": "inquiry_letter", "name": "收到监管问询函未回复", "weight": 0.5}, ...],
               "hard_avoid": False}
    """
    try:
        # 1. 先检查本地缓存（本进程内）
        import os
        import json as _json
        from datetime import datetime
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "event_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"events_{code}.json")
        
        # 尝试从文件缓存读取（缓存1天）
        if os.path.exists(cache_file):
            age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if age < 86400:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return _json.load(f)
        
        # 2. 从突发事件检测模块获取数据
        events = []
        hard_avoid = False
        try:
            from backend.services.event_detector import _query_cninfo
            
            # 硬规避事件检查（直接CNINFO查询）
            hard_keywords = {
                "fraud_investigation": "财务造假",
                "audit_negative_opinion": "无法表示意见",
                "debt_default": "债务违约",
                "public_censure": "行政处罚",
            }
            for evt_key, keyword in hard_keywords.items():
                results = _query_cninfo(keyword)
                for r in results:
                    if r["code"] == code:
                        events.append({
                            "key": evt_key,
                            "name": ALL_EVENTS.get(evt_key, evt_key),
                            "weight": EVENT_WEIGHTS.get(evt_key, 999),
                        })
                        if evt_key in HARD_AVOID_EVENTS:
                            hard_avoid = True
                        break
                        
            # 一般事件检查
            normal_keywords = {
                "inquiry_letter": "问询函",
                "accounting_error": "前期会计差错更正",
            }
            for evt_key, keyword in normal_keywords.items():
                results = _query_cninfo(keyword)
                for r in results:
                    if r["code"] == code:
                        events.append({
                            "key": evt_key,
                            "name": ALL_EVENTS.get(evt_key, evt_key),
                            "weight": EVENT_WEIGHTS.get(evt_key, 0.5),
                        })
                        break
        except Exception as e:
            logger.warning(f"事件检测失败 {code}: {e}")
        
        result = {"events": events, "hard_avoid": hard_avoid}
        
        # 写入文件缓存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                _json.dump(result, f, ensure_ascii=False)
        except Exception:
            pass
        
        return result
    except Exception as e:
        logger.warning(f"加载事件 {code} 失败: {e}")
        return {"events": [], "hard_avoid": False}


async def _async_load_events(code: str) -> Dict[str, Any]:
    """异步从数据库加载事件数据"""
    try:
        from backend.config.database import async_session_factory
        from backend.models.warning import WarningConfig
        from sqlalchemy import select
        async with async_session_factory() as session:
            stmt = select(WarningConfig).where(
                WarningConfig.config_type == "event",
                WarningConfig.code == code,
                WarningConfig.is_active == True,
            )
            result = await session.execute(stmt)
            configs = result.scalars().all()
            events = []
            hard_avoid = False
            for cfg in configs:
                evt_key = cfg.params.get("event_key", "")
                if evt_key in EVENT_WEIGHTS:
                    events.append({
                        "key": evt_key,
                        "name": ALL_EVENTS.get(evt_key, evt_key),
                        "weight": EVENT_WEIGHTS[evt_key],
                    })
                    if evt_key in HARD_AVOID_EVENTS:
                        hard_avoid = True
            return {"events": events, "hard_avoid": hard_avoid}
    except Exception as e:
        logger.warning(f"异步加载事件失败 {code}: {e}")
        return {"events": [], "hard_avoid": False}


def _load_events_sync(code: str) -> Dict[str, Any]:
    """同步方式从数据库加载事件（降级）"""
    try:
        from backend.config.database import SessionLocal
        from backend.models.warning import WarningConfig
        db = SessionLocal()
        try:
            configs = db.query(WarningConfig).filter(
                WarningConfig.config_type == "event",
                WarningConfig.code == code,
                WarningConfig.is_active == True,
            ).all()
            events = []
            hard_avoid = False
            for cfg in configs:
                evt_key = cfg.params.get("event_key", "")
                if evt_key in EVENT_WEIGHTS:
                    events.append({
                        "key": evt_key,
                        "name": ALL_EVENTS.get(evt_key, evt_key),
                        "weight": EVENT_WEIGHTS[evt_key],
                    })
                    if evt_key in HARD_AVOID_EVENTS:
                        hard_avoid = True
            return {"events": events, "hard_avoid": hard_avoid}
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"同步加载事件失败 {code}: {e}")
        return {"events": [], "hard_avoid": False}


# ─── 主函数 ─────────────────────────────────────

def check_event_warning(
    code: str,
    name: str,
    price: float = 0,
    pre_close: float = 0,
    open_price: float = 0,
    high_price: float = 0,
    low_price: float = 0,
    volumes: List[float] = None,
    closes: List[float] = None,
    turnover_rate: float = None,
    historical_turnovers: List[float] = None,
    thresholds: Dict[str, Any] = None,
    event_data: Dict[str, Any] = None,
) -> Optional[WarningResult]:
    """
    按设计文档6.3.6节计算突发预警。

    每日开盘前加载一次事件数据，交易日期间不实时变化。
    非交易时段用上次加载的结果。
    Returns:
        始终返回非None（即使无事件也返回绿色安全）
    """
    # 获取该股票的事件数据
    event_data = event_data or get_stock_events(code)
    events = event_data.get("events", [])
    hard_avoid = event_data.get("hard_avoid", False)

    # 计算总分
    total_score = sum(e["weight"] for e in events if e["weight"] < 999)

    # 颜色
    color = score_to_color(total_score, hard_avoid)
    triggered = color != "green"

    # 构建详情
    event_details = [
        {"key": e["key"], "name": e["name"], "weight": e["weight"]}
        for e in events
    ]
    hard_avoid_items = [
        {"key": e["key"], "name": e["name"]}
        for e in events if e["key"] in HARD_AVOID_EVENTS
    ]

    level_map = {"green": "info", "yellow": "warning", "red": "danger", "black": "critical"}
    level = level_map.get(color, "info")
    label = score_to_label(total_score, hard_avoid)

    # 标题
    if hard_avoid:
        title = f"{name}({code}) 突发规避【{'; '.join(e['name'] for e in hard_avoid_items)}】"
    elif total_score >= 2:
        title = f"{name}({code}) 突发风险({total_score:.0f}分)"
    elif total_score > 0:
        title = f"{name}({code}) 小幅异动({total_score:.1f}分)"
    else:
        title = f"{name}({code}) 无突发事件"

    detail = {
        "code": code,
        "name": name,
        "event_score": total_score,
        "label": label,
        "events": event_details,
        "hard_avoid": hard_avoid,
        "hard_avoid_items": hard_avoid_items,
    }

    return WarningResult(
        code=code,
        warning_type="event",
        warning_level=level,
        title=title,
        detail=str(detail),
        indicator_color=color,
        triggered=triggered,
    )
