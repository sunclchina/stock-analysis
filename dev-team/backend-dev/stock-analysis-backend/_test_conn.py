import akshare as ak
# Test if akshare can even connect
try:
    # Try getting basic stock info to confirm akshare works
    df = ak.stock_info_a_code_name()
    print(f"stock_info_a_code_name: {len(df)} stocks - OK")
except Exception as e:
    print(f"stock_info_a_code_name FAILED: {e}")

# Try a direct HTTP call to East Money push2 for limit-up data
import httpx
url = "https://push2.eastmoney.com/api/qt/clist/get"
params = {
    "pn": 1, "pz": 10, "po": 1, "np": 1,
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": 2, "invt": 2, "fid": "f3",
    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
    "fields": "f12,f14,f2,f3",
}
try:
    with httpx.Client(timeout=10) as c:
        r = c.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        print(f"East Money push2: HTTP {r.status_code}")
        d = r.json()
        total = d.get("data",{}).get("total",0)
        print(f"  total stocks: {total}")
except Exception as e:
    print(f"East Money push2 FAILED: {e}")
