"""
市场扩展服务——移植自 go-stock 的全球指数、行业排名、资金流向等高级市场数据。
数据源：腾讯财经 QQ Finance + 新浪财经 + 东方财富。
"""

import logging
from datetime import datetime, timedelta
import httpx
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MarketExtensionService:
    """市场扩展数据服务"""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=10.0)

    async def _get_commodities(self) -> List[Dict[str, Any]]:
        """获取商品/外汇数据（新浪财经）"""
        url = "https://hq.sinajs.cn/list=hf_GC,hf_CL,fx_susdcny"
        try:
            resp = await self._client.get(url, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            text = resp.text
            items = []
            for line in text.split(";"):
                if not line.strip():
                    continue
                # 解析新浪期货格式:
                # hf_GC="最新价,涨跌,买价,卖价,最高,最低,时间,昨收,今开,持仓量,成交量,?,日期,名称,?"
                # 使用昨收(index 7)作为显示价，涨跌幅用(最新价-昨收)/昨收
                if "hf_GC" in line or "hf_CL" in line:
                    parts = line.split('\"')[1].split(',')
                    name = str(parts[-2]) if len(parts) > 2 else ""
                    latest = self._safe_float(parts[0]) if len(parts) > 0 else 0
                    prev_close = self._safe_float(parts[7]) if len(parts) > 7 else 0
                    price = prev_close if prev_close > 0 else latest
                    change_pct = round((latest - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0
                    code = "GC" if "hf_GC" in line else "CL"
                    items.append({"code": code, "name": name, "price": price, "change_pct": change_pct})
                elif "fx_susdcny" in line:
                    parts = line.split('\"')[1].split(',')
                    if len(parts) > 1:
                        price = self._safe_float(parts[1])
                        items.append({"code": "USDCNY", "name": "美元兑人民币", "price": price, "change_pct": 0})
            return items
        except Exception as e:
            logger.warning(f"商品/外汇数据获取失败: {e}")
            return []

    @staticmethod
    def _safe_float(v) -> float:
        try:
            return float(str(v).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _days_ago(days: int) -> str:
        """返回 N 天前的日期字符串 YYYY-MM-DD"""
        return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # ── 全球指数 ───────────────────────────────────────────

    async def get_global_indices(self) -> Dict[str, Any]:
        """获取全球主要指数行情"""
        url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/rank/indexRankDetail2"
        try:
            resp = await self._client.get(url, headers={
                "Referer": "https://stockapp.finance.qq.com/mstats",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("data", {})
            result = self._format_global_indices(raw)
            # 追加商品/外汇数据
            commodities = await self._get_commodities()
            if commodities:
                result["groups"].append({"name": "商品/外汇", "items": commodities})
                result["count"] += len(commodities)
            return result
        except Exception as e:
            logger.warning(f"全球指数获取失败: {e}")
            return {"groups": [], "count": 0}

    def _format_global_indices(self, raw: dict) -> Dict[str, Any]:
        """格式化全球指数数据（QQ API 字段：zxj=最新价, zdf=涨跌幅%）"""
        groups = []
        for group_name in ["common", "america", "europe", "asia", "other"]:
            items = raw.get(group_name, [])
            if not items:
                continue
            group_label = {
                "common": "综合", "america": "美洲", "europe": "欧洲",
                "asia": "亚太", "other": "其他",
            }.get(group_name, group_name)
            formatted = []
            for item in items:
                zxj_str = str(item.get("zxj", "0"))
                zdf_str = str(item.get("zdf", "0"))
                try:
                    price = float(zxj_str.replace(",", ""))
                except ValueError:
                    price = 0
                try:
                    change_pct = float(zdf_str.replace(",", ""))
                except ValueError:
                    change_pct = 0
                formatted.append({
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "price": price,
                    "change_pct": change_pct,
                })
            groups.append({"name": group_label, "items": formatted})
        return {"groups": groups, "count": sum(len(g["items"]) for g in groups)}

    # ── 行业排名 ───────────────────────────────────────────

    async def get_industry_ranking(self, sort: str = "0", count: int = 20) -> List[Dict[str, Any]]:
        """获取行业涨幅排名"""
        url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank?l={count}&p=1&t=01/averatio&ordertype=&o={sort}"
        try:
            resp = await self._client.get(url, headers={
                "Referer": "https://stockapp.finance.qq.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            data = resp.json()
            return self._format_industry_ranking(data)
        except Exception as e:
            logger.warning(f"行业排名获取失败: {e}")
            return []

    def _format_industry_ranking(self, data: dict) -> List[Dict[str, Any]]:
        """格式化行业排名（QQ API 字段）"""
        items = data.get("data", [])
        results = []
        for item in items:
            results.append({
                "name": item.get("bd_name", ""),
                "code": item.get("bd_code", ""),
                "price": self._safe_float(item.get("bd_zxj", "0")),
                "avg_change_pct": self._safe_float(item.get("bd_zdf", "0")),
                "change_5d": self._safe_float(item.get("bd_zdf5", "0")),
                "change_20d": self._safe_float(item.get("bd_zdf20", "0")),
                "leading_stock": item.get("nzg_name", ""),
                "leading_stock_code": item.get("nzg_code", ""),
                "leading_stock_price": self._safe_float(item.get("nzg_zxj", "0")),
                "leading_stock_change": self._safe_float(item.get("nzg_zdf", "0")),
            })
        return results

    # ── 行业资金流向（新浪）────────────────────────────────

    async def get_industry_money_flow(self, sort: str = "netamount", fenlei: str = "0") -> List[Dict[str, Any]]:
        """获取行业资金流向排名"""
        url = (
            f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"MoneyFlow.ssl_bkzj_bk?page=1&num=20&sort={sort}&asc=0&fenlei={fenlei}"
        )
        try:
            resp = await self._client.get(url, headers={
                "Host": "vip.stock.finance.sina.com.cn",
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"行业资金流向获取失败: {e}")
            return []

    # ── 个股资金流向（新浪）────────────────────────────────

    async def get_stock_money_flow(self, sort: str = "netamount") -> List[Dict[str, Any]]:
        """获取个股资金流向排名（新浪财经）"""
        url = (
            f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
            f"MoneyFlow.ssl_bkzj_bk?page=1&num=50&sort={sort}&asc=0&fenlei=1"
        )
        try:
            resp = await self._client.get(url, headers={
                "Host": "vip.stock.finance.sina.com.cn",
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            resp.raise_for_status()
            raw_list = resp.json()
            # 格式化字段
            results = []
            for item in raw_list:
                results.append({
                    "code": item.get("ts_symbol", ""),
                    "name": item.get("ts_name", ""),
                    "trade": item.get("avg_price", item.get("ts_trade", "0")),
                    "changepercent": item.get("avg_changeratio", "0"),
                    "turnover": item.get("turnover", "0"),
                    "inamount": item.get("inamount", "0"),
                    "outamount": item.get("outamount", "0"),
                    "netamount": item.get("netamount", "0"),
                    "ratioamount": item.get("ratioamount", "0"),
                    "ts_changeratio": item.get("ts_changeratio", "0"),
                    "ts_ratioamount": item.get("ts_ratioamount", "0"),
                })
            return results
        except Exception as e:
            logger.warning(f"个股资金流向获取失败: {e}")
            return []

    # ── 1. 个股研报 ─────────────────────────────────────────────────

    async def get_stock_research_report(self, stock_code: str, days: int = 365) -> Dict[str, Any]:
        """获取个股研报（东方财富 reportapi）"""
        today = datetime.now().strftime("%Y-%m-%d")
        days_ago = self._days_ago(days)
        url = "https://reportapi.eastmoney.com/report/list2"
        payload = {
            "code": stock_code,
            "industryCode": "*",
            "beginTime": days_ago,
            "endTime": today,
            "pageNo": 1,
            "pageSize": 50,
            "p": 1,
            "pageNum": 1,
            "pageNumber": 1,
        }
        headers = {
            "Host": "reportapi.eastmoney.com",
            "Origin": "https://data.eastmoney.com",
            "Referer": "https://data.eastmoney.com/report/stock.jshtml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        }
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # 安全取 resp.data（可能返回 list 或 dict）
            result = data.get("data", data.get("Data", data.get("result", data)))
            if isinstance(result, str):
                # 尝试安全转换
                pass
            return result
        except Exception as e:
            logger.warning(f"个股研报获取失败 ({stock_code}): {e}")
            return {"items": [], "total": 0}

    # ── 2. 公司公告 ─────────────────────────────────────────────────

    async def get_stock_notice(self, stock_codes: str, page_size: int = 10) -> Dict[str, Any]:
        """获取公司公告（东方财富）"""
        codes = stock_codes.replace(",", "%2C")
        url = (
            f"https://np-anotice-stock.eastmoney.com/api/security/ann"
            f"?page_size={page_size}&page_index=1"
            f"&ann_type=SHA%2CCYB%2CSZA%2CBJA%2CINV"
            f"&client_source=web&f_node=0&stock_list={codes}"
        )
        headers = {
            "Host": "np-anotice-stock.eastmoney.com",
            "Referer": "https://data.eastmoney.com/notices/hsa/5.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = await self._client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("list", [])
        except Exception as e:
            logger.warning(f"公司公告获取失败 ({stock_codes}): {e}")
            return []

    # ── 3. 行业研究 ─────────────────────────────────────────────────

    async def get_industry_research_report(self, industry_code: str = "", days: int = 7) -> Dict[str, Any]:
        """获取行业研究报告（东方财富 reportapi）"""
        today = datetime.now().strftime("%Y-%m-%d")
        days_ago = self._days_ago(days)
        params = {
            "industry": "*",
            "industryCode": industry_code,
            "beginTime": days_ago,
            "endTime": today,
            "pageNo": 1,
            "pageSize": 50,
            "p": 1,
            "pageNum": 1,
            "pageNumber": 1,
            "qType": 1,
        }
        headers = {
            "Host": "reportapi.eastmoney.com",
            "Origin": "https://data.eastmoney.com",
            "Referer": "https://data.eastmoney.com/report/stock.jshtml",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = await self._client.get(
                "https://reportapi.eastmoney.com/report/list",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data.get("Data", {}))
        except Exception as e:
            logger.warning(f"行业研报获取失败 ({industry_code}): {e}")
            return {"items": [], "total": 0}

    # ── 4. 指标选股 ─────────────────────────────────────────────────

    async def get_indicator_selection(self, keyword: str, qgqp_b_id: str = "") -> Dict[str, Any]:
        """指标选股（东方财富选股器）

        Args:
            keyword: 自然语言选股条件
            qgqp_b_id: 东财用户标识（从系统设置传入），空字符串时尝试走无标识模式
        """
        import time
        timestamp = int(time.time())
        url = "https://np-tjxg-g.eastmoney.com/api/smart-tag/stock/v3/pw/search-code"
        fingerprint = qgqp_b_id if qgqp_b_id else str(timestamp)
        payload = {
            "keyWord": keyword,
            "pageSize": 20,
            "pageNo": 1,
            "fingerprint": fingerprint,
            "gids": [],
            "matchWord": "",
            "timestamp": timestamp,
            "shareToGuba": False,
            "requestId": "",
            "needCorrect": True,
            "removedConditionIdList": [],
            "xcId": "",
            "ownSelectAll": False,
            "dxInfo": [],
            "extraCondition": "",
        }
        headers = {
            "Host": "np-tjxg-g.eastmoney.com",
            "Origin": "https://xuangu.eastmoney.com",
            "Referer": "https://xuangu.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        }
        if qgqp_b_id:
            headers["Cookie"] = f"qgqp_b_id={qgqp_b_id}"
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"指标选股获取失败: {e}")
            return {"code": -1, "data": {"result": {"dataList": [], "columns": []}}}

    # ── 5. 涨停梯队 & 6. 异动监控（共享同一个行情API）───────────────

    async def get_market_stock_list(self) -> List[Dict[str, Any]]:
        """获取全市场实时行情列表（涨停/异动共用，带磁盘缓存）"""
        cache_file = "data/a_share_cache/market_stock_list.json"
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f15,f16,f17,f18",
        }
        headers = {
            "Host": "push2.eastmoney.com",
            "Referer": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            resp = await self._client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            raw_list = (data.get("data", {}) or {}).get("diff", [])
            if not raw_list:
                # API返回空数据，尝试读缓存
                try:
                    import json
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    if cached.get("stocks"):
                        logger.info(f"全市场行情: 使用缓存 ({cached.get('date','?')})")
                        return cached["stocks"]
                except Exception:
                    pass
                return []
            results = []
            for item in raw_list:
                results.append({
                    "code": str(item.get("f12", "")),
                    "name": str(item.get("f14", "")),
                    "price": self._safe_float(item.get("f2", 0)),
                    "change_pct": self._safe_float(item.get("f3", 0)),
                    "change_amount": self._safe_float(item.get("f4", 0)),
                    "volume": self._safe_float(item.get("f5", 0)),
                    "amount": self._safe_float(item.get("f6", 0)),
                    "amplitude": self._safe_float(item.get("f7", 0)),
                    "turnover_rate": self._safe_float(item.get("f8", 0)),
                    "high": self._safe_float(item.get("f15", 0)),
                    "low": self._safe_float(item.get("f16", 0)),
                    "open": self._safe_float(item.get("f17", 0)),
                    "pre_close": self._safe_float(item.get("f18", 0)),
                })
            # 缓存到磁盘
            try:
                import json
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"stocks": results, "date": datetime.now().strftime("%Y-%m-%d")}, f, ensure_ascii=False)
            except Exception:
                pass
            return results
        except Exception as e:
            logger.warning(f"全市场行情获取失败: {e}")
            # 尝试读缓存
            try:
                import json
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if cached.get("stocks"):
                    logger.info(f"全市场行情: 异常后使用缓存 ({cached.get('date','?')})")
                    return cached["stocks"]
            except Exception:
                pass
            return []

    async def get_limit_up_tier(self) -> Dict[str, Any]:
        """获取涨停梯队（涨幅 >= 9.8%）"""
        stock_list = await self.get_market_stock_list()
        limit_up_stocks = [s for s in stock_list if s["change_pct"] >= 9.8]
        # 按涨幅降序排列
        limit_up_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        # 简单分组：首板（无连板信息）、连板（仅做标识，实际连板天数需额外API）
        # 按涨停类型分组
        tier_groups = {
            "stocks": [],
            "count": 0,
        }
        for s in limit_up_stocks:
            # 标记类型（简化：涨幅高且换手率低的归为强势板）
            tier_type = "首板"
            if s["turnover_rate"] < 5 and s["change_pct"] >= 9.9:
                tier_type = "强势首板"
            tier_groups["stocks"].append({
                "code": s["code"],
                "name": s["name"],
                "price": s["price"],
                "change_pct": s["change_pct"],
                "turnover_rate": s["turnover_rate"],
                "amplitude": s["amplitude"],
                "tier_type": tier_type,
            })
        tier_groups["count"] = len(tier_groups["stocks"])
        return tier_groups

    async def get_anomaly_monitor(self) -> Dict[str, Any]:
        """获取异动监控列表"""
        stock_list = await self.get_market_stock_list()
        anomaly_stocks = []
        for s in stock_list:
            chg = s["change_pct"]
            tr = s["turnover_rate"]
            amp = s["amplitude"]
            anomaly_types = []
            if chg >= 5:
                anomaly_types.append("急速拉升")
            if chg <= -5:
                anomaly_types.append("大幅下跌")
            if tr >= 10:
                anomaly_types.append("放量异动")
            if amp >= 8:
                anomaly_types.append("剧烈波动")
            if anomaly_types:
                anomaly_stocks.append({
                    "code": s["code"],
                    "name": s["name"],
                    "price": s["price"],
                    "change_pct": chg,
                    "turnover_rate": tr,
                    "amplitude": amp,
                    "anomaly_type": "、".join(anomaly_types),
                })
        # 按异常严重程度排序：异动类型越多越靠前，同样数量按涨幅绝对值排序
        anomaly_stocks.sort(key=lambda x: (-len(x["anomaly_type"].split("、")), -abs(x["change_pct"])))
        return {
            "stocks": anomaly_stocks,
            "count": len(anomaly_stocks),
            "anomaly_categories": {
                "急速拉升": sum(1 for s in anomaly_stocks if "急速拉升" in s["anomaly_type"]),
                "大幅下跌": sum(1 for s in anomaly_stocks if "大幅下跌" in s["anomaly_type"]),
                "放量异动": sum(1 for s in anomaly_stocks if "放量异动" in s["anomaly_type"]),
                "剧烈波动": sum(1 for s in anomaly_stocks if "剧烈波动" in s["anomaly_type"]),
            },
        }

    # ── 7. 个股研报详情（全文）───────────────────────────────────────────────

    async def get_stock_report_detail(self, info_code: str) -> Dict[str, Any]:
        """获取个股研报详情全文

        从东方财富研报详情页获取内容，返回标题和全文。
        """
        if not info_code:
            return {"title": "", "content": "", "note": "缺少研报编号"}
        pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"
        html_url = f"https://data.eastmoney.com/report/zw/stock/{info_code}.html"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/report/stock.jshtml",
            }
            try:
                resp = await client.get(html_url, headers=headers)
                if resp.status_code == 200:
                    import re
                    html = resp.text
                    title = ""
                    tm = re.search(r'<title>([^<]+)</title>', html)
                    if tm:
                        title = tm.group(1).strip()
                    content = ""
                    for pattern in [
                        r'<div[^>]*class="ctx-content"[^>]*>([\s\S]*?)</div>',
                        r'<div[^>]*class="news-content"[^>]*>([\s\S]*?)</div>',
                        r'<div[^>]*class="report-content"[^>]*>([\s\S]*?)</div>',
                        r'<div[^>]*class="detail-content"[^>]*>([\s\S]*?)</div>',
                        r'<article[^>]*>([\s\S]*?)</article>',
                    ]:
                        cm = re.search(pattern, html)
                        if cm:
                            content = cm.group(1).strip()
                            break
                    if content:
                        content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content)
                        content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content)
                        content = re.sub(r'<br\s*/?>', '\n', content)
                        content = re.sub(r'<p[^>]*>', '\n', content)
                        content = re.sub(r'</p>', '', content)
                        content = re.sub(r'<[^>]+>', '', content)
                        content = re.sub(r'\n{3,}', '\n\n', content)
                        content = content.strip()
                    if title or content:
                        return {
                            "title": title,
                            "content": content[:10000],
                            "pdf_url": pdf_url,
                            "source": "html",
                        }
            except Exception:
                pass
        return {
            "title": "",
            "content": "",
            "pdf_url": pdf_url,
            "source": "pdf_only",
            "note": "暂未获取到全文，可在新窗口查看PDF原文",
        }
