"""Try to auto-fetch qgqp_b_id from East Money xuan gu page"""
import httpx

url = "https://xuangu.eastmoney.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

with httpx.Client(timeout=15, follow_redirects=True) as c:
    r = c.get(url, headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Headers:")
    for k, v in r.headers.items():
        if "cookie" in k.lower() or "set" in k.lower():
            print(f"  {k}: {v[:200]}")

    print(f"\nCookies in session:")
    for k, v in c.cookies.items():
        print(f"  {k}: {str(v)[:100]}")
        if "qgqp" in k.lower():
            print(f"  *** FOUND qgqp_b_id = {v}")
