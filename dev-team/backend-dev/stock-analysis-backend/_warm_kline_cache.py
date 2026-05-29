"""
K线缓存预热脚本。
遍历指定股票池，调用K线API并缓存结果。
运行一次后形态选股在周末也有数据。
"""
import asyncio, sys, json, httpx
from pathlib import Path

sys.path.insert(0, ".")

CACHE_DIR = Path("data/kline_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

async def warm_one(client, code):
    """获取单只股票K线并缓存"""
    cache_file = CACHE_DIR / f"{code}.json"
    if cache_file.exists():
        return  # 已有缓存
    
    try:
        r = await client.get(
            f"http://localhost:8000/api/v1/market/kline/{code}?count=120",
            timeout=10
        )
        d = r.json()
        klines = d.get("klines", [])
        if klines:
            data = {
                "code": code,
                "cached_at": __import__("datetime").datetime.now().isoformat(),
                "count": len(klines),
                "klines": klines,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            return True
    except Exception:
        return False

async def main():
    # 获取股票列表
    print("获取股票代码列表...")
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {"pn": "1", "pz": "5000", "po": "1", "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2", "invt": "2", "fid": "f3",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81,m:0 t:82",
        "fields": "f12,f14"}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        codes = [i["f12"] for i in d.get("data",{}).get("diff",[])]
    
    print(f"共 {len(codes)} 只股票，开始预热K线缓存...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        done = 0
        for i, code in enumerate(codes[:500]):  # 前500只
            result = await warm_one(client, code)
            if result:
                done += 1
            if (i + 1) % 50 == 0:
                print(f"  进度: {i+1}/{min(len(codes),500)}, 缓存: {done} 只")
    
    print(f"完成！已缓存 {done} 只股票的K线数据")

if __name__ == "__main__":
    asyncio.run(main())
