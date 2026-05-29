"""Test eastmoney batch turnover rate API"""
import httpx
url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
params = {"fltt": "2", "invt": "2", "fields": "f12,f14,f8", "secids": "1.600519,0.000001"}
with httpx.Client(timeout=10) as c:
    r = c.get(url, params=params, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com"})
    d = r.json()
    print(f"Status: {r.status_code}")
    print(f"Response: {d}")
    diff = d.get("data", {}).get("diff", [])
    for item in diff:
        print(f"code={item.get('f12')} name={item.get('f14')} f8={item.get('f8')}")
