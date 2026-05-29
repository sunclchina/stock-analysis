#!/usr/bin/env python3
import urllib.request, json

data = json.dumps({"code": "600519", "name": "Guizhou MT"}).encode()
req = urllib.request.Request(
    'http://localhost:8000/api/v1/config/monitor',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    r = urllib.request.urlopen(req, timeout=5)
    print('ADD MONITOR:', r.status, r.read().decode()[:200])
except Exception as e:
    print('ADD MONITOR error:', str(e)[:100])

try:
    r2 = urllib.request.urlopen('http://localhost:8000/api/v1/config/monitor', timeout=5)
    body = r2.read().decode()
    print('GET MONITOR:', r2.status, body[:300])
except Exception as e:
    print('GET MONITOR error:', str(e)[:100])

data2 = json.dumps({"code": "000858", "name": "Wuliangye"}).encode()
req3 = urllib.request.Request(
    'http://localhost:8000/api/v1/config/watchlist',
    data=data2,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    r3 = urllib.request.urlopen(req3, timeout=5)
    print('ADD WATCHLIST:', r3.status, r3.read().decode()[:200])
except Exception as e:
    print('ADD WATCHLIST error:', str(e)[:100])

try:
    r4 = urllib.request.urlopen('http://localhost:8000/api/v1/config/watchlist', timeout=5)
    body4 = r4.read().decode()
    print('GET WATCHLIST:', r4.status, body4[:300])
except Exception as e:
    print('GET WATCHLIST error:', str(e)[:100])
