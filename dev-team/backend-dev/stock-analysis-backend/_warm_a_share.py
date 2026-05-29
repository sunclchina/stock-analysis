"""
A股概况缓存预热脚本。
独立运行(非uvicorn线程)，用同步方式调用akshare获取北交所和ETF数据，
写入磁盘缓存供仪表盘读取。
"""
import json, os, sys
from pathlib import Path

# 写入到与 backend 一致的路径（相对于项目根）
cache_dir = Path(__file__).parent / "data" / "a_share_cache"
cache_dir.mkdir(parents=True, exist_ok=True)
cache_file = cache_dir / "stock_codes.json"

print("正在获取全市场股票代码...")
import akshare as ak
df = ak.stock_info_a_code_name()
codes = df['code'].tolist()

# 按前缀统计
sh_main = sum(1 for c in codes if str(c).startswith(("600","601","603","605")))
sh_star = sum(1 for c in codes if str(c).startswith(("688","689")))
sh_b = sum(1 for c in codes if str(c).startswith("900"))
sz_main = sum(1 for c in codes if str(c).startswith(("000","001","002","003","004")))
sz_gem = sum(1 for c in codes if str(c).startswith(("300","301")))
sz_b = sum(1 for c in codes if str(c).startswith("200"))
bj = sum(1 for c in codes if str(c).startswith(
    ("920","430","830","831","832","833","834","835","836","837","838","839","870","871","872","873")))
print(f"沪市{sh_main+sh_star+sh_b} 深市{sz_main+sz_gem+sz_b} 北交所{bj}")

print("正在获取ETF数据...")
etf = ak.fund_etf_spot_em()
esh = sum(1 for c in etf['代码'].tolist() if str(c).startswith(("51","52","56","58")))
esz = sum(1 for c in etf['代码'].tolist() if str(c).startswith("159"))
print(f"ETF: 沪{esh} + 深{esz} = {esh+esz}")

result = {
    "shanghai": {
        "total": sh_main+sh_star+sh_b,
        "main_board": {"count": sh_main, "prefixes": ["600","601","603","605"]},
        "star": {"count": sh_star, "prefixes": ["688"]},
        "b_share": {"count": sh_b, "prefixes": ["900"]},
    },
    "shenzhen": {
        "total": sz_main+sz_gem+sz_b,
        "main_board": {"count": sz_main, "prefixes": ["000","001","002","003","004"]},
        "gem": {"count": sz_gem, "prefixes": ["300","301"]},
        "b_share": {"count": sz_b, "prefixes": ["200"]},
    },
    "beijing": {"total": bj, "all": {"count": bj, "prefixes": ["920"]}},
    "etf": {"shanghai": {"count": esh, "prefixes": ["51","52","56","58"]},
            "shenzhen": {"count": esz, "prefixes": ["159"]}, "total": esh+esz},
    "total_stock_count": len(codes),
    "generated_at": __import__('datetime').datetime.now().isoformat(),
}
with open(cache_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
print(f"已写入 {cache_file}")
print("完成")
