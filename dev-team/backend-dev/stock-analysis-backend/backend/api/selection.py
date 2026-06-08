"""M04 选股API（v3.0）"""
import asyncio, os, struct, logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Body, Path, Query
from backend.services.selection_engine import (
    fixed_selection, custom_selection,
    selection_task_queue, TaskStatus,
    financial_data_loader, batch_filter,
)
from backend.services.selection_engine.fixed import _enrich_technicals
from backend.utils.indicators import calc_ma
from backend.services.data_source.fallback import DataSourceManager, DataSourceUnavailableError

logger = logging.getLogger(__name__)

# 延迟获取 data_source_manager
_data_source_manager = None

def _get_dsm():
    """延迟获取数据源管理器"""
    global _data_source_manager
    if _data_source_manager is None:
        from backend.main import data_source_manager
        _data_source_manager = data_source_manager
    return _data_source_manager

router = APIRouter(tags=["selection"], prefix="/selection")

TDX = [("sh", r"C:\zd_zxzq_gm\vipdoc\sh\lday"), ("sz", r"C:\zd_zxzq_gm\vipdoc\sz\lday")]
PRE = {'600','601','603','605','688','000','001','002','003','300','301','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873','920'}
SZX = {'000','001','002','003','300','301','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873','920'}

def _rd(filepath):
    if not os.path.isfile(filepath): return None
    with open(filepath, "rb") as f: data = f.read()
    rc = len(data) // 32
    if rc < 25: return None
    cs, vs, hs, ls = [], [], [], []
    for i in range(rc):
        off = i * 32
        rec = data[off:off+32]
        if len(rec) < 32: break
        cp = struct.unpack("<i", rec[16:20])[0] / 100.0
        if cp <= 0: continue
        cs.append(cp); vs.append(float(struct.unpack("<i", rec[24:28])[0]))
        hs.append(struct.unpack("<i", rec[8:12])[0] / 100.0)
        ls.append(struct.unpack("<i", rec[12:16])[0] / 100.0)
    if len(cs) < 25: return None
    return {"c":cs,"v":vs,"h":hs,"l":ls,"lc":cs[-1],"pc":cs[-2] if len(cs)>=2 else cs[-1],"lv":vs[-1],"la":struct.unpack("<i",data[-12:-8])[0]/10000.0 if len(data)>=12 else 0}

async def _load_from_tdx():
    st, se = [], set()
    for mk, ld in TDX:
        if not os.path.isdir(ld): continue
        for fn in os.listdir(ld):
            if not fn.endswith(".day"): continue
            rw = fn[:-4]; cd = rw[2:] if rw[:2] in ('sh','sz','bj') else rw
            if cd[:3] not in PRE or cd in se: continue
            if mk == 'sh' and cd[:3] in SZX: continue
            se.add(cd)
            dd = _rd(os.path.join(ld, fn))
            if not dd: continue
            cs, vs, hs, ls = dd["c"], dd["v"], dd["h"], dd["l"]
            pr, pc, vl, am = dd["lc"], dd["pc"], dd["lv"], dd["la"]
            n = len(cs)
            m5 = next((v for v in reversed(calc_ma(cs,5)) if v is not None), pr)
            m10 = next((v for v in reversed(calc_ma(cs,10)) if v is not None), pr)
            m20 = next((v for v in reversed(calc_ma(cs,20)) if v is not None), pr)
            m20v = [v for v in calc_ma(cs,20) if v is not None]
            m20u = len(m20v) >= 5 and m20v[-1] > m20v[-5]
            lb = min(60, n)
            ps = (pr - min(cs[-lb:])) / (max(cs[-lb:]) - min(cs[-lb:]) + 0.001)
            c3 = (cs[-1]-cs[-4])/cs[-4]*100 if n>=4 else 0
            v5 = sum(vs[-6:-1])/5 if n>=6 else (sum(vs[-2:])/2 if n>=2 else vl)
            vr = vl/v5 if v5>0 else 1.0
            dr = (pr-m20)/m20*100 if m20>0 else 0
            st.append({"code":cd,"name":cd,"exchange":"sh" if mk=="sh" else "sz","price":pr,"pre_close":pc,
                "change_pct":0,"change_pct_3d":round(c3,2),"amount":am,"volume":vl,"volumes":vs,"closes":cs,
                "highs":hs,"lows":ls,"ma5":m5,"ma10":m10,"ma20":m20,"ma20_trend_up":m20u,
                "prev_volume":vs[-2] if len(vs)>=2 else vl*0.9,"volume_5d_avg":round(v5,2),"volume_ratio":round(vr,2),
                "price_position":round(ps,4),"deviation_rate":round(dr,2),
                "is_st":False,"is_suspended":False,"circ_market_value":0,"trade_days_since_listing":n,
                "trend_direction":"","trend_score":50,"resonance_positive_count":0,"resonance_negative_count":0,
                "risk_score":50,
                "finance_grade":"yellow","finance_color":"yellow","finance_abnormal_count":0,"deducted_profit":0,
                "profit_growth":-50,"net_profit_growth":-50,"operate_cashflow":0,"debt_ratio":60.0,"roe":0,
                "fraud_flag":False,"audit_opinion":"standard","planned_reduction_pct":0,"pledge_ratio":0,
                "pledge_forced_liquidation":False,"debt_default_flag":False,"csrc_investigation_flag":False,
                "lawsuit_amount":0,"net_asset":1000000000,"public_censure_flag":False,"event_score":0,
                "consecutive_drop_volume_days":0,"breakdown_signal":False})
            if len(st) >= 6000: break
        if len(st) >= 6000: break
    return st


def _parse_sina_simple_json(text: str) -> list:
    """解析Sina返回的JSON数组响应（可能带括号包裹）"""
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        t = t[1:-1]
    if not t or t == "[]":
        return []
    import json
    return json.loads(t)


async def _load_from_sina():
    """从新浪在线API加载全市场股票 — 优先使用 akshare 快速获取列表"""
    import asyncio
    import httpx
    import pandas as _pd
    st = []
    try:
        # 优先使用 akshare 获取全量股票代码（~8秒，在线程池运行避免阻塞事件循环）
        all_codes = []
        try:
            import akshare as _ak
            loop = asyncio.get_running_loop()
            _df = await loop.run_in_executor(None, _ak.stock_info_a_code_name)
            if _df is not None and not _df.empty:
                seen = set()
                for _, row in _df.iterrows():
                    code = str(row['code'])
                    name = str(row['name'])
                    if code[:3] in PRE and code not in seen:
                        seen.add(code)
                        all_codes.append({"code": code, "name": name})
                logger.info(f"选股代码列表(akshare): {len(all_codes)} 只")
        except Exception as e:
            logger.warning(f"akshare 股票列表失败: {e}")
        
        if not all_codes:
            # 回退：新浪 MarketCenter API（慢但可靠）
            import httpx
            loop = asyncio.get_event_loop()
            def _fetch_code_list():
                import httpx as _hx
                all_codes = []
                seen = set()
                nodes = ["sh_a", "sz_a", "bj_a"]
                with _hx.Client(timeout=30, verify=False) as cl:
                    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
                    for node in nodes:
                        page = 1
                        empty_pages = 0
                        while page <= 100:
                            try:
                                params = {"page": str(page), "num": "100", "sort": "code", "asc": "1", "node": node}
                                resp = cl.get(url, params=params, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://vip.stock.finance.sina.com.cn/"})
                                items = _parse_sina_simple_json(resp.text)
                            except Exception:
                                break
                            if not items:
                                empty_pages += 1
                                if empty_pages >= 3:
                                    break
                                page += 1
                                continue
                            empty_pages = 0
                            for item in items:
                                sym = str(item.get("symbol", "")).strip()
                                code = sym[2:] if sym.startswith(("sh", "sz", "bj")) else sym
                                name = str(item.get("name", code)).strip()
                                if code and code not in seen and code[:3] in PRE:
                                    seen.add(code)
                                    tr_raw = item.get("turnoverratio")
                                    mc_raw = item.get("mktcap")
                                    all_codes.append({"code": code, "name": name,
                                        "turnover_rate": float(tr_raw) if tr_raw and str(tr_raw) else None,
                                        "circ_market_value": float(mc_raw) if mc_raw and str(mc_raw) else 0})
                            if len(items) < 100:
                                break
                            page += 1
                return all_codes
            all_codes = await loop.run_in_executor(None, _fetch_code_list)
        if not all_codes:
            logger.warning("新浪选股: MarketCenter返回空")
            return st
        logger.info(f"新浪选股: MarketCenter返回 {len(all_codes)} 只股票")

        # 第二步：用 Sina 批量行情补充价格（每次最多50只）
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=10) as client:
            for i in range(0, len(all_codes), 50):
                batch = all_codes[i:i+50]
                codes_str = ",".join([f"sh{c['code']}" if c['code'].startswith(('6','9')) else f"sz{c['code']}" for c in batch])
                try:
                    resp = await client.get(
                        f"https://hq.sinajs.cn/list={codes_str}",
                        headers=headers
                    )
                    text = resp.text
                    for cinfo in batch:
                        cd = cinfo["code"]
                        nm = cinfo["name"]
                        tr = cinfo.get("turnover_rate")
                        cmv = cinfo.get("circ_market_value", 0)
                        prefix = f"sh{cd}" if cd.startswith(('6','9')) else f"sz{cd}"
                        marker = f'var hq_str_{prefix}="'
                        pos = text.find(marker)
                        if pos >= 0:
                            end = text.find('";', pos)
                            if end > pos:
                                parts = text[pos+len(marker):end].split(",")
                                pr = float(parts[3]) if len(parts) > 3 and parts[3] else 0
                                pc = float(parts[2]) if len(parts) > 2 and parts[2] else pr
                                cp = round((pr - pc) / pc * 100, 2) if pc > 0 else 0
                                vl = float(parts[8]) if len(parts) > 8 else 0
                                am = float(parts[9]) if len(parts) > 9 else 0
                                st.append({"code": cd, "name": nm, "exchange": "sh" if cd.startswith(('6','9')) else "sz",
                                    "price": pr, "pre_close": pc, "change_pct": cp, "change_pct_3d": 0,
                                    "amount": am, "volume": vl, "volumes": [vl]*60, "closes": [pr]*60,
                                    "highs": [pr]*60, "lows": [pr]*60,
                                    "ma5": pr, "ma10": pr, "ma20": pr, "ma20_trend_up": True,
                                    "prev_volume": vl, "volume_5d_avg": vl, "volume_ratio": 1.0,
                                    "turnover_rate": tr,
                                    "is_st": "ST" in nm.upper() or "*ST" in nm.upper(),
                                    "is_suspended": False, "circ_market_value": cmv,
                                    "trade_days_since_listing": 60,
                                    "trend_direction": "", "trend_score": 50,
                                    "resonance_positive_count": 0, "resonance_negative_count": 0,
                                    "risk_score": 50,
                                    "finance_grade": "yellow", "finance_color": "yellow", "finance_abnormal_count": 0,
                                    "deducted_profit": 0, "profit_growth": -50, "net_profit_growth": -50,
                                    "operate_cashflow": 0, "debt_ratio": 60.0, "roe": 0,
                                    "fraud_flag": False, "audit_opinion": "standard",
                                    "planned_reduction_pct": 0, "pledge_ratio": 0,
                                    "pledge_forced_liquidation": False, "debt_default_flag": False,
                                    "csrc_investigation_flag": False, "lawsuit_amount": 0,
                                    "net_asset": 1000000000, "public_censure_flag": False,
                                    "event_score": 0, "consecutive_drop_volume_days": 0, "breakdown_signal": False})
                except Exception as e:
                    logger.warning(f"新浪选股: 第{i}批失败: {e}")
                    continue
        logger.info(f"新浪选股: 完成，共 {len(st)} 只")

        # 第三步：通过新浪K线数据补充MA指标
        async def _fetch_kline_for_one(code: str) -> dict:
            """获取单只股票的K线数据并计算MA指标（需 sh/sz 前缀）"""
            try:
                sina_code = f"sh{code}" if code.startswith(("6","9")) else f"sz{code}"
                url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_code}&scale=240&datalen=90"
                async with httpx.AsyncClient(timeout=8) as c:
                    resp = await c.get(url, headers={"Referer": "https://finance.sina.com.cn"})
                    data = resp.json()
                if not data or len(data) < 20:
                    return None
                closes = []
                volumes = []
                for item in data:
                    try:
                        closes.append(float(item.get("close", 0)))
                        volumes.append(float(item.get("volume", 0)))
                    except (ValueError, TypeError):
                        continue
                if len(closes) < 20:
                    return None
                return {
                    "closes": closes,
                    "volumes": volumes,
                    "price": closes[-1],
                    "ma5": sum(closes[-5:])/5,
                    "ma10": sum(closes[-10:])/10,
                    "ma20": sum(closes[-20:])/20,
                    "ma20_trend_up": sum(closes[-5:])/5 > sum(closes[-10:-5])/5 if len(closes) >= 10 else True,
                    "volume_5d_avg": sum(volumes[-6:-1])/5 if len(volumes) >= 6 else volumes[-1] if volumes else 0,
                    "change_pct_3d": (closes[-1]-closes[-4])/closes[-4]*100 if len(closes) >= 4 else 0,
                }
            except Exception:
                return None

        # 分批补充K线MA（取前500只大盘股，每批20个并发，保证L1-L4通过率）
        batch_size = 20
        kline_limit = min(len(st), 500)
        for start_idx in range(0, kline_limit, batch_size):
            batch = st[start_idx:start_idx+batch_size]
            tasks = [_fetch_kline_for_one(s["code"]) for s in batch]
            kline_results = await asyncio.gather(*tasks, return_exceptions=True)
            for s, kr in zip(batch, kline_results):
                if kr and isinstance(kr, dict):
                    s["price"] = kr.get("price", s["price"])
                    s["ma5"] = kr.get("ma5", s["ma5"])
                    s["ma10"] = kr.get("ma10", s["ma10"])
                    s["ma20"] = kr.get("ma20", s["ma20"])
                    s["ma20_trend_up"] = kr.get("ma20_trend_up", True)
                    s["volume_5d_avg"] = kr.get("volume_5d_avg", s["volume"])
                    s["volume_ratio"] = s["volume"] / s["volume_5d_avg"] if s["volume_5d_avg"] > 0 else 1.0
                    s["change_pct_3d"] = kr.get("change_pct_3d", 0)
                    kl = kr.get("closes", [s["price"]]*60)
                    hp = max(kl[-60:]) if len(kl) >= 60 else max(kl)
                    lp = min(kl[-60:]) if len(kl) >= 60 else min(kl)
                    s["price_position"] = (s["price"]-lp)/(hp-lp+0.001) if hp > lp else 0.5
                    s["closes"] = kl + [s["price"]] * max(0, 60 - len(kl))
                    s["volumes"] = kr.get("volumes", [s["volume"]]*60) + [s["volume"]] * max(0, 60 - len(kr.get("volumes", [s["volume"]])))
                    s["prev_volume"] = kr.get("volumes", [s["volume"]])[-2] if len(kr.get("volumes", [s["volume"]])) >= 2 else s["volume"]
            await asyncio.sleep(0.1)  # 节流
        logger.info(f"新浪选股: K线MA补充完成")

    except Exception as e:
        logger.error(f"新浪选股失败: {e}")
    return st


async def _load_from_api():
    """从东方财富在线API加载全市场股票行情 — 使用 clist/get 按板块批量查询"""
    st = []
    try:
        import httpx
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        fields = "f12,f14,f2,f3,f4,f5,f6,f8,f15,f16,f17,f18,f20,f103"
        # 按板块分批：沪市主板/科创板, 深市主板/创业板/中小板, 北交所
        boards = [
            ("m:0+t:6,m:0+t:80", "沪A"),   # 沪市主板+科创板
            ("m:1+t:2,m:1+t:23", "深A"),    # 深市主板+创业板
            ("m:0+t:81", "北A"),            # 北交所(如有)
        ]
        for fs, label in boards:
            for page in range(1, 11):  # 最多10页，每页200只 = 2000只/板块
                params = {
                    "pn": str(page), "pz": "200", "po": "1", "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2", "invt": "2", "fid": "f3",
                    "fs": fs, "fields": fields,
                }
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        resp = await client.get(url, params=params, headers=headers)
                        data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", []) if data else []
                    if not items:
                        break  # 无更多数据
                    for it in items:
                        cd = str(it.get("f12", ""))
                        if cd and cd[:3] in PRE:
                            st.append(_make_stock_dict(cd, it))
                    if len(items) < 200:
                        break  # 最后一页
                except Exception as e2:
                    logger.warning(f"选股API: {label}第{page}页失败: {e2}")
                    break
            if len(st) >= 6000:
                break
        logger.info(f"选股API: 完成，共 {len(st)} 只股票")
    except Exception as e:
        logger.error(f"选股API失败: {e}")
    return st


def _make_stock_dict(code, data):
    name = str(data.get("f14") or data.get("name") or code)
    pr = float(data.get("f2") or data.get("price") or 0)
    pc = float(data.get("f18") or 0)
    cp = float(data.get("f3") or 0)
    vl = float(data.get("f5") or 0)
    am = float(data.get("f6") or 0)
    hp = float(data.get("f15") or 0)
    lp = float(data.get("f16") or 0)
    turnover_raw = data.get("f8")
    industry_raw = data.get("f103") or ""
    return {"code":code,"name":name,"exchange":"sh" if code[0] in ('6','9') else "sz",
        "price":pr,"pre_close":pc,"change_pct":cp,"change_pct_3d":0,
        "amount":am,"volume":vl,"volumes":[vl]*60,"closes":[pr]*60,
        "highs":[max(hp,pr)]*60,"lows":[min(lp,pr)]*60,
        "ma5":pr,"ma10":pr,"ma20":pr,"ma20_trend_up":True,
        "prev_volume":vl,"volume_5d_avg":vl,"volume_ratio":1.0,
        "price_position":0.5,"deviation_rate":0,
        "turnover_rate": float(turnover_raw) if turnover_raw is not None and str(turnover_raw).replace('.','',1).lstrip('-').isdigit() else None,
        "industry": industry_raw if isinstance(industry_raw, str) else "",
        "is_st":False,"is_suspended":pr<=0,
        "circ_market_value":0,"trade_days_since_listing":60,
        "trend_direction":"","trend_score":50,
        "resonance_positive_count":0,"resonance_negative_count":0,
        "risk_score":50,
        "finance_grade":"yellow","finance_color":"yellow","finance_abnormal_count":0,"deducted_profit":0,
        "profit_growth":-50,"net_profit_growth":-50,"operate_cashflow":0,"debt_ratio":60.0,"roe":0,
        "fraud_flag":False,"audit_opinion":"standard","planned_reduction_pct":0,"pledge_ratio":0,
        "pledge_forced_liquidation":False,"debt_default_flag":False,"csrc_investigation_flag":False,
        "lawsuit_amount":0,"net_asset":1000000000,"public_censure_flag":False,"event_score":0,
        "consecutive_drop_volume_days":0,"breakdown_signal":False}


# 模块级缓存：选股数据只加载一次，后续秒回（5分钟）
_cache = {"stocks": None, "timestamp": 0}
_CACHE_TTL = 300

async def _enrich_parallel(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """并行执行 enrichment 和 ST/停牌标记，带超时控制"""
    # 预加载财务缓存
    await financial_data_loader.load(stocks)
    tasks = [
        asyncio.create_task(_mark_st_stop(stocks)),
    ]
    try:
        done, pending = await asyncio.wait(tasks, timeout=15)
        for t in pending:
            t.cancel()
            logger.warning(f"enrich任务超时取消: {t}")
    except Exception as e:
        logger.warning(f"enrich部分失败: {e}")
    return stocks


async def _mark_st_stop(stocks: List[Dict[str, Any]]) -> None:
    """标记ST和停牌股票（通过模块数据源映射）"""
    dsm = _get_dsm()
    loop = asyncio.get_event_loop()
    
    try:
        source = dsm.get_active_for_module("selection_st")
        
        if source.name in ("akshare", "akshare_em"):
            try:
                import akshare as ak
                st_df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_zh_a_st_em()),
                    timeout=8
                )
                if st_df is not None and not st_df.empty:
                    st_codes = set(st_df["代码"].astype(str).str.strip())
                    for s in stocks:
                        if s["code"] in st_codes:
                            s["is_st"] = True
                    logger.info(f"ST标记完成：{len(st_codes)}只ST股")
            except:
                logger.warning("ST标记超时或失败")
            try:
                import akshare as ak
                stop_df = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: ak.stock_zh_a_stop_em()),
                    timeout=8
                )
                if stop_df is not None and not stop_df.empty:
                    stop_codes = set(stop_df["代码"].astype(str).str.strip())
                    for s in stocks:
                        if s["code"] in stop_codes:
                            s["is_suspended"] = True
                    logger.info(f"停牌标记完成：{len(stop_codes)}只停牌股")
            except:
                logger.warning("停牌标记超时或失败")
        
        elif source.name == "eastmoney":
            # 东方财富API - 通过涨跌幅 = 0 和行情数据判断停牌
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as c:
                    url = "https://push2.eastmoney.com/api/qt/clist/get"
                    params = {
                        "pn": "1", "pz": "5000", "po": "0", "np": "1",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                        "fltt": "2", "invt": "2", "fid": "f3",
                        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2",
                        "fields": "f12,f2,f3,f14",
                    }
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"}
                    resp = await c.get(url, params=params, headers=headers)
                    data = resp.json()
                    items = (data.get("data", {}) or {}).get("diff", [])
                    if items:
                        code_map = {}
                        for it in items:
                            cd = str(it.get("f12", ""))
                            nm = str(it.get("f14", "")).upper()
                            if "ST" in nm or "*ST" in nm:
                                code_map[cd] = "st"
                            pr = it.get("f2")
                            if pr is None or (isinstance(pr, str) and pr == "-"):
                                code_map[cd] = "suspended"
                        for s in stocks:
                            flag = code_map.get(s["code"])
                            if flag == "st":
                                s["is_st"] = True
                            elif flag == "suspended":
                                s["is_suspended"] = True
                        logger.info(f"东财ST/停牌标记完成：{sum(1 for v in code_map.values() if v == 'st')}只ST")
            except Exception as e:
                logger.warning(f"东财ST/停牌标记失败: {e}")
    except DataSourceUnavailableError as e:
        logger.warning(f"ST/停牌数据源不可用: {e}")


async def load():
    now = datetime.now().timestamp()
    if _cache["stocks"] and (now - _cache["timestamp"]) < _CACHE_TTL:
        logger.info(f"选股数据使用缓存: {len(_cache['stocks'])} 只")
        return _cache["stocks"]
    
    # 通过数据源模块映射获取股票池数据
    dsm = _get_dsm()
    pool_sources = dsm.get_module_sources("selection_pool")
    st = []
    # 优先使用新浪（东财push2在此网络被HTTPS拦截）
    logger.info(f"选股数据源顺序: {pool_sources}")
    for sname in pool_sources:
        if sname == "tdx_local" and dsm._tdx_enabled:
            logger.info(f"尝试TDX...")
            st = await _load_from_tdx()
            if st:
                logger.info(f"选股数据来自TDX: {len(st)} 只")
                break
        elif sname == "sina":
            logger.info(f"尝试Sina...")
            st = await _load_from_sina()
            logger.info(f"Sina返回: {len(st) if st else 0} 只")
            if st:
                logger.info(f"选股数据来自Sina: {len(st)} 只")
                break
        elif sname == "eastmoney":
            logger.info(f"尝试EastMoney...")
            st = await _load_from_api()
            if st:
                logger.info(f"选股数据来自EastMoney: {len(st)} 只")
                break
    


    # 从本地缓存补充东方财富字段（换手率、行业）
    if st:
        try:
            from backend.services.eastmoney_enricher import get_enricher
            enricher = get_enricher()
            await enricher.enrich_stocks(st)
        except Exception as e:
            logger.warning(f"东财富集(load)失败: {e}")

    if not st:
        logger.warning("所有选股数据源均不可用")
    logger.info(f"选股数据加载完成: {len(st)} 只")
    _cache["stocks"] = st
    _cache["timestamp"] = now
    return st


def period():
    n = datetime.now()
    if n.weekday() >= 5: return "非交易日快照"
    t = n.hour*60+n.minute
    if 510<=t<555: return "盘前快照"
    elif 555<=t<690: return "盘中实时"
    elif 690<=t<780: return "午休快照"
    elif 780<=t<905: return "盘中实时"
    elif 905<=t<960: return "收盘定稿"
    else: return "非交易日快照"


def _format_stock_result(s: Dict[str, Any]) -> Dict[str, Any]:
    dc = {"bullish":"red","reversal":"blue","consolidation":"yellow","bearish":"green","unknown":"gray","up":"red","bullish_reversal":"blue"}
    td = s.get("trend_direction","unknown")
    rs = min(s.get("risk_score",60) or 60, 100)
    rp = s.get("resonance_positive_count",0) or 0
    rl = "low" if rs <= 40 else ("medium" if rs <= 60 else "high")
    rs_ = "多头共振" if rp >= 6 else ("多头" if rp >= 4 else ("空头" if rp <= 1 else "中性"))
    ind = s.get("industry", "") or ""
    return {
        "rank": 0,
        "code": s.get("code",""),
        "name": s.get("name",""),
        "industry": ind,
        "price": s.get("price",0),
        "change_pct": s.get("change_pct",0),
        "trendColor": dc.get(td,"gray"),
        "resonanceStatus": rs_,
        "trendStrength": abs(s.get("trend_score",0) or 0),
        "riskScore": rs,
        "riskLevel": rl,
        "financeGrade": {"green":"A","yellow":"B","red":"C"}.get(s.get("finance_grade",""),"B"),
        "compositeScore": round(s.get("total_score", s.get("composite_score",0)) or 0, 1),
        "operationAdvice": s.get("trade_advice","不推荐"),
        "turnoverRate": s.get("turnover_rate"),
        "addedToWatchlist": False,
    }


async def _enrich_finance(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """财务数据 enrichment（通过 FinancialDataLoader 缓存）"""
    # 改用金融预加载器
    await financial_data_loader.load(stocks)
    for s in stocks:
        financial_data_loader.enrich_stock(s)
    has_data = sum(1 for s in stocks if s.get("finance_data_available", False))
    logger.info(f"财务数据 enrichment: {has_data}/{len(stocks)} 只有数据")
    return stocks


async def fill_names(items):
    """填充股票名称、实时行情、行业等数据"""
    if not items: return items
    cds = [i["code"] for i in items]
    try:
        dsm = _get_dsm()
        qs = await dsm.get_quotes(cds)
        if qs:
            qm = {}
            for q in qs:
                if not q: continue
                qm[q.code] = q
            for i in items:
                q = qm.get(i["code"])
                if not q: continue
                if hasattr(q, 'name') and q.name and (not i.get('name') or i['name'] == i['code']):
                    i["name"] = q.name
                    n = i["name"].upper()
                    if "ST" in n or "*ST" in n: i["is_st"] = True
                if q.price and q.price > 0:
                    i["price"] = q.price
                if hasattr(q, 'change_pct'):
                    i["change_pct"] = q.change_pct or 0
                if hasattr(q, 'change'):
                    i["change"] = q.change or 0
                if q.volume and q.volume > 0:
                    i["volume"] = q.volume
                if q.amount and q.amount > 0:
                    i["amount"] = q.amount
                if hasattr(q, 'turnover_rate') and q.turnover_rate > 0:
                    i["turnover_rate"] = q.turnover_rate
    except Exception as e:
        logger.warning(f"行情数据填充失败: {e}")
    
    need_industry = [i for i in items if not i.get("industry") or i["industry"] == ""]
    if need_industry:
        try:
            import httpx
            import asyncio
            loop = asyncio.get_event_loop()
            industry_map = {}
            # 方法1：使用东方财富行业板块成分股接口（单次调用，5秒超时）
            try:
                headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com"}
                sec_url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
                sec_params = {
                    "reportName": "RPT_BOARD_INDUSTRY_NEW",
                    "columns": "INDUSTRY_CODE,INDUSTRY_NAME,SECURITY_CODE",
                    "pageNumber": 1,"pageSize": 5000,
                    "sortTypes": -1,"sortColumns": "INDUSTRY_CODE",
                    "source": "WEB","client": "WEB",
                }
                async with httpx.AsyncClient(timeout=8) as client:
                    resp = await client.get(sec_url, params=sec_params, headers=headers)
                    if resp.status_code == 200:
                        sec_data = resp.json()
                        if sec_data.get("success"):
                            for row in (sec_data.get("data", {}) or {}).get("list", []):
                                cd = str(row.get("SECURITY_CODE", "")).strip()
                                ind = str(row.get("INDUSTRY_NAME", "")).strip()
                                if cd and ind:
                                    industry_map[cd] = ind
                            logger.info(f"行业数据API: 获取{len(industry_map)}条")
            except Exception as e:
                logger.warning(f"行业数据API失败: {e}")
            # 方法2：通过个股查询（每只股票一个API）
            if not industry_map:
                try:
                    import akshare as ak
                    for stock in need_industry[:20]:  # 最多查20只
                        try:
                            df = await loop.run_in_executor(
                                None,
                                lambda cd=stock["code"]: ak.stock_individual_info_em(symbol=cd)
                            )
                            if df is not None and not df.empty:
                                ind_row = df[df["item"] == "行业"]
                                if not ind_row.empty:
                                    industry_map[stock["code"]] = str(ind_row.iloc[0]["value"])
                        except Exception:
                            pass
                    logger.info(f"行业数据akshare: 获取{len(industry_map)}条")
                except ImportError:
                    pass
            # 合并结果
            assigned = 0
            for stock in need_industry:
                cd = stock["code"]
                ind = industry_map.get(cd, "")
                if ind:
                    stock["industry"] = ind
                    assigned += 1
            logger.info(f"行业数据填充: 共{len(need_industry)}只, 成功{assigned}只")
        except Exception as e:
            logger.warning(f"行业数据填充失败: {e}")
    return items


# 自定义模板存储
CUSTOM_TEMPLATES: Dict[str, Any] = {}


@router.get("/fixed")
async def f_get(
    template_id: str = Query("steady_trend", description="模板ID"),
    limit: int = Query(None, ge=1, le=100, description="返回数量上限")
):
    """固定选股（GET版本，支持前端直接调用）"""
    return await _run_fixed_selection(template_id, limit)


@router.post("/fixed")
async def f(body: Dict[str,Any]=Body(..., examples={"default": {"value": {"template_id": "steady_trend"}}})):
    tid = body.get("template_id") or body.get("strategy","steady_trend")
    mr = body.get("max_results") or body.get("limit")
    mr = None if mr is None else max(1,min(100,int(mr)))
    return await _run_fixed_selection(tid, mr)


async def _run_fixed_selection(tid: str, max_results: Optional[int] = None):
    """固定选股核心逻辑（GET和POST共用，v3.0）"""
    valid_strategies = ["steady_trend", "reversal_breakout", "short_term_strong"]
    TEMPLATE_ID_MAP = {
        "stable_trend": "steady_trend",
        "reversal_breakthrough": "reversal_breakout",
    }
    resolved_id = TEMPLATE_ID_MAP.get(tid, tid)
    if resolved_id not in valid_strategies:
        raise HTTPException(400, detail=f"未知ID: {tid}")
    mr = max_results
    if mr is not None:
        mr = max(1, min(100, int(mr)))
    ss = await load()
    total = len(ss)
    if not ss: return {"items":[],"count":0,"message":"暂无股票"}

    ss = await _enrich_parallel(ss)
    ss = await _enrich_finance(ss)

    r = fixed_selection(resolved_id, ss, max_results=mr)
    results = await fill_names(r.get("results",[]))
    r["results"] = results

    label = period()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_notes = {
        "盘前快照": "盘前快照（基于昨日收盘）",
        "盘中实时": "实时数据",
        "午休快照": "午休期间数据无更新",
        "收盘定稿": "收盘定稿数据",
        "非交易日快照": "非交易日数据无更新",
    }

    items = []
    for i, s in enumerate(r.get("results",[])):
        item = _format_stock_result(s)
        item["rank"] = i + 1
        items.append(item)

    grade_counts = r.get("grade_counts", {})
    logger.info(f"Output: {len(items)} items, 分级={grade_counts}")
    return {
        "items": items,
        "count": len(items),
        "total_count": total,
        "template": r.get("template", {}),
        "layer_counts": r.get("layer_counts", {}),
        "grade_counts": grade_counts,
        "trading_session": {"label":label,"note":session_notes.get(label,""),"timestamp":ts},
        "data_period_label": label,
        "data_timestamp": ts,
        "capacity": mr or 20,
        "message": f"完成: {len(items)} 只",
    }


@router.post("/custom")
async def c(body: Dict[str,Any]=Body(..., examples={"default": {"value": {
    "dimensions": {"scope": {}, "technical": {"ma_type": "bullish"}},
    "max_results": 100
}}})):
    ss = await load()
    if not ss:
        return {"items":[],"count":0,"message":"暂无股票", "step_counts":{}}

    ss = await _enrich_finance(ss)
    await _mark_st_stop(ss)

    max_results = min(body.get("max_results", 100), 500)
    r = await custom_selection(body, ss, max_results=max_results)
    
    results = await fill_names(r.get("results", []))
    label = period()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    items = []
    for i, s in enumerate(results):
        item = _format_stock_result(s)
        item["rank"] = i + 1
        items.append(item)

    message = r.get("message", f"完成: {len(items)} 只")
    session_notes = {
        "盘前快照": "盘前快照（基于昨日收盘）",
        "盘中实时": "实时数据",
        "午休快照": "午休期间数据无更新",
        "收盘定稿": "收盘定稿数据",
        "非交易日快照": "非交易日数据无更新",
    }
    return {
        "items": items,
        "count": len(items),
        "template": {"id":"custom","name":"自定义选股","description":"用户自定义条件"},
        "step_counts": r.get("step_counts", {}),
        "elapsed_seconds": r.get("elapsed_seconds", 0),
        "truncated": r.get("truncated", False),
        "trading_session": {"label":label,"note":session_notes.get(label,""),"timestamp":ts},
        "data_period_label": label,
        "data_timestamp": ts,
        "capacity": max_results,
        "message": message,
    }


@router.get("/custom-templates")
async def list_custom_templates():
    return {"templates": [{"id":tid,**v} for tid,v in CUSTOM_TEMPLATES.items()]}


@router.post("/custom-templates")
async def save_custom_template(body: dict = Body(...)):
    name = body.get("name","")
    conditions = body.get("conditions",[])
    logic = body.get("logic","and")
    dimensions = body.get("dimensions", {})
    if not name or (not conditions and not dimensions):
        raise HTTPException(400,"名称和条件不能为空")
    import hashlib, json
    payload = json.dumps(conditions or dimensions)
    tid = hashlib.md5(f"{name}_{payload}".encode()).hexdigest()[:12]
    CUSTOM_TEMPLATES[tid] = {"name":name,"conditions":conditions,"dimensions":dimensions,
        "logic":logic,
        "max_results":body.get("max_results",100),"created_at":datetime.now().isoformat()}
    logger.info(f"自定义模板已保存: {tid} - {name}")
    return {"success":True,"template":{"id":tid,"name":name}}


@router.delete("/custom-templates/{template_id}")
async def delete_custom_template(template_id: str = Path(..., description="模板ID")):
    if template_id not in CUSTOM_TEMPLATES:
        raise HTTPException(404, detail=f"模板不存在: {template_id}")
    del CUSTOM_TEMPLATES[template_id]
    logger.info(f"自定义模板已删除: {template_id}")
    return {"success":True}


@router.get("/templates")
async def list_templates():
    from backend.services.selection_engine.fixed import SELECTION_TEMPLATES as REG
    return {"templates":[{"id":tid,"name":t.get("name",""),"description":t.get("description",""),"max_results":t.get("max_results",0)} for tid,t in REG.items()]}


@router.get("/period")
async def p():
    return {"data_period_label":period(),"data_timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


@router.get("/industries")
async def industries():
    try:
        import akshare as ak
        import asyncio
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: ak.stock_board_industry_name_em())
        if df is not None and not df.empty:
            col = [c for c in df.columns if "名称" in c]
            if col:
                return {"items": df[col[0]].dropna().unique().tolist()}
    except:
        pass
    COMMON = ["银行","证券","保险","房地产","建筑","建材","钢铁","煤炭","石油","化工","有色","电力","新能源","汽车","机械","军工","通信","电子","计算机","软件","医药","食品饮料","白酒","家电","纺织","轻工","商贸","旅游","传媒","环保","公用事业","交通运输","农林牧渔"]
    return {"items": COMMON}


# ═══════════════════════════════════════════════════
# 异步任务队列 API (v3.0)
# ═══════════════════════════════════════════════════


@router.post("/submit")
async def submit_selection_task(body: dict = Body(..., examples={"default": {"value": {
    "strategy": "steady_trend",
    "max_results": 20,
}}})):
    """异步提交选股任务"""
    strategy = body.get("strategy", body.get("strategy_id", "steady_trend"))
    max_results = body.get("max_results", 20)
    dimensions = body.get("dimensions", {})

    valid_strategies = ["steady_trend", "reversal_breakout", "short_term_strong", "custom"]
    if strategy not in valid_strategies:
        raise HTTPException(400, detail=f"未知策略: {strategy}")

    # 作为后台任务提交
    async def execute_selection(tid: str, mr: int, dims: dict):
        """后台执行选股"""
        ss = await load()
        if not ss:
            return {"results": [], "count": 0, "layer_counts": {}}
        ss = await _enrich_parallel(ss)
        await _mark_st_stop(ss)

        if tid == "custom" and dims:
            result = await custom_selection({"dimensions": dims}, ss, max_results=mr)
            return {
                "results": result.get("results", []),
                "count": result.get("count", 0),
                "step_counts": result.get("step_counts", {}),
            }
        else:
            result = fixed_selection(tid, ss, max_results=mr)
            return {
                "results": result.get("results", []),
                "count": result.get("count", 0),
                "layer_counts": result.get("layer_counts", {}),
                "grade_counts": result.get("grade_counts", {}),
            }

    task_id = selection_task_queue.submit(
        strategy=strategy,
        params={"tid": strategy, "mr": max_results, "dims": dimensions},
        execute_func=execute_selection,
    )

    return {
        "task_id": task_id,
        "status": "pending",
        "strategy": strategy,
        "message": "选股任务已提交",
    }


@router.get("/task/{task_id}")
async def get_task_result(task_id: str = Path(..., description="任务ID")):
    """查询任务状态/结果"""
    result = selection_task_queue.get_result(task_id)
    if result is None:
        raise HTTPException(404, detail=f"任务不存在: {task_id}")

    # 如果已完成，格式化结果
    if result.get("status") == "completed" and result.get("result"):
        raw_results = result["result"].get("results", [])
        formatted = []
        for i, s in enumerate(raw_results):
            item = _format_stock_result(s)
            item["rank"] = i + 1
            formatted.append(item)

        return {
            **result,
            "items": formatted,
            "count": len(formatted),
        }

    return result


@router.get("/cached")
async def get_cached_results():
    """获取缓存的最新选股结果（条件相同的最新结果）"""
    # 获取最近3个已完成的任务
    all_tasks = selection_task_queue.get_queue_status()
    return {
        "queue": all_tasks,
        "message": "通过 GET /selection/task/{task_id} 查询具体任务结果",
    }


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str = Path(..., description="任务ID")):
    """取消选股任务"""
    success = selection_task_queue.cancel_task(task_id)
    if not success:
        raise HTTPException(404, detail=f"任务不存在或无法取消: {task_id}")
    return {"success": True, "message": f"任务已取消: {task_id}"}


@router.get("/queue")
async def get_queue_status():
    """获取队列状态"""
    return selection_task_queue.get_queue_status()
