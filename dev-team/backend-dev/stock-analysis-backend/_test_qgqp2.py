"""Try multiple approaches to get qgqp_b_id automatically"""
import httpx, re, json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://xuangu.eastmoney.com/",
}

# Approach 1: Call the smart-tag search API without fingerprint, see what it returns
print("=== Approach 1: smart-tag API (no fingerprint) ===")
url = "https://np-tjxg-g.eastmoney.com/api/smart-tag/stock/v3/pw/search-code"
payload = {
    "keyWord": "量比大于2",
    "pageSize": 5,
    "pageNo": 1,
    "fingerprint": "",
    "timestamp": __import__('time').time() * 1000,
}
try:
    with httpx.Client(timeout=10) as c:
        r = c.post(url, json=payload, headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:300]}")
        print(f"Set-Cookie: {r.headers.get('set-cookie', 'none')}")
except Exception as e:
    print(f"Failed: {e}")

# Approach 2: Visit xuangu main page with a session
print("\n=== Approach 2: Visit xuangu main page ===")
try:
    with httpx.Client(timeout=15) as c:
        r = c.get("https://xuangu.eastmoney.com/", headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Cookies: {dict(c.cookies)}")
except Exception as e:
    print(f"Failed: {e}")

# Approach 3: The fingerprint generation API
print("\n=== Approach 3: Try common generation endpoints ===")
endpoints = [
    "https://np-tjxg-g.eastmoney.com/api/smart-tag/fingerprint/generate",
    "https://np-tjxg-g.eastmoney.com/api/smart-tag/user/fingerprint",
    "https://data.eastmoney.com/api/fingerprint",
]
for ep in endpoints:
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(ep, headers=headers)
            print(f"{ep}: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"{ep}: Failed - {e}")
