import httpx
import json
r = httpx.get('http://127.0.0.1:8000/api/v1/config/datasource', timeout=10)
d = r.json()
print(f'Active: {d.get("active_source")}')
print(f'Primary: {d.get("primary_source")}')
print()
for s in d.get('sources', []):
    active = ' <-- ACTIVE' if s.get('is_active') else ''
    print(f'{s["name"]:15s} status={s["status"]:10s} failures={s.get("consecutive_failures",0)}{active}')
