"""
K线缓存直接预热脚本。
使用akshare直接获取A股K线数据并写入缓存目录。
不依赖后端HTTP服务，速度更快。
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, ".")

CACHE_DIR = Path("data/kline_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

print("获取股票列表...")
import akshare as ak
df = ak.stock_info_a_code_name()
codes = df['code'].tolist()
print(f"共 {len(codes)} 只股票")

# 只预热前500只（流动性最好的）
codes = codes[:500]
done = 0
errors = 0
start = time.time()

for i, code in enumerate(codes):
    cf = CACHE_DIR / f"{code}.json"
    if cf.exists():
        done += 1
        continue
    
    try:
        # 从akshare获取日K线（前复权）
        kdf = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20250101", adjust="qfq")
        if kdf is not None and not kdf.empty:
            klines = []
            for _, row in kdf.tail(120).iterrows():
                klines.append({
                    "date": str(row["日期"])[:10],
                    "open": float(row["开盘"]),
                    "close": float(row["收盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "volume": float(row["成交量"]),
                    "amount": float(row["成交额"]),
                })
            data = {
                "code": code,
                "cached_at": __import__("datetime").datetime.now().isoformat(),
                "count": len(klines),
                "klines": klines,
            }
            with open(cf, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            done += 1
    except Exception as e:
        errors += 1
    
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start
        print(f"  进度: {i+1}/{len(codes)}, 成功: {done}, 失败: {errors}, 耗时: {elapsed:.0f}s")

elapsed = time.time() - start
print(f"\n完成！已缓存 {done} 只, 失败 {errors} 只, 总耗时 {elapsed:.0f}s")
print(f"缓存目录: {CACHE_DIR.absolute()}")
