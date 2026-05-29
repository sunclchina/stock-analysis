"""
Generate seed cache for limit-up and market stock data.
Used as a warmup to populate cache with last trading day's data.
"""
import json, sys
from pathlib import Path

cache_dir = Path("data/a_share_cache")
cache_dir.mkdir(parents=True, exist_ok=True)

print("Trying to get the most recent available market data...")

# Strategy: Use akshare to get a broad stock list that works on weekends
try:
    import akshare as ak
    # stock_info_a_code_name works 24/7
    df = ak.stock_info_a_code_name()
    print(f"Got stock list: {len(df)} stocks")
    
    # Get spot data (might work on weekends with cached data)
    spot = ak.stock_zh_a_spot()
    if spot is not None and not spot.empty:
        print(f"Got spot data: {len(spot)} stocks")
        
        # Build market stock list cache
        stocks = []
        for _, row in spot.iterrows():
            stocks.append({
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": float(row.get("最新价", 0)),
                "change_pct": float(row.get("涨跌幅", 0)),
                "volume": float(row.get("成交量", 0)),
                "amount": float(row.get("成交额", 0)),
                "amplitude": float(row.get("振幅", 0)),
                "turnover_rate": float(row.get("换手率", 0)),
            })
        
        if stocks:
            with open(cache_dir / "market_stock_list.json", "w", encoding="utf-8") as f:
                json.dump({"stocks": stocks, "date": "昨交易日"}, f, ensure_ascii=False)
            print(f"Saved market_stock_list cache: {len(stocks)} stocks")
            
            # Also find limit-up stocks
            limit_up = [s for s in stocks if s["change_pct"] >= 9.8]
            if limit_up:
                # Sort by change_pct descending
                limit_up.sort(key=lambda x: x["change_pct"], reverse=True)
                for s in limit_up:
                    s["limit_up_reason"] = ""
                    s["limit_up_times"] = ""
                    s["limit_up_type"] = ""
                with open(cache_dir / "limit_up_cache.json", "w", encoding="utf-8") as f:
                    json.dump({"stocks": limit_up, "date": "昨交易日"}, f, ensure_ascii=False)
                print(f"Saved limit_up cache: {len(limit_up)} stocks")
            else:
                print("No limit-up stocks in current data (weekend)")
    else:
        print("Spot data empty")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
