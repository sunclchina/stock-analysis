import httpx
r = httpx.get('http://127.0.0.1:8000/api/v1/config/datasource', timeout=10)
d = r.json()
print('Active:', d.get('active_source'))
print('Primary:', d.get('primary_source'))
print('Fallback:', d.get('fallback_source'))
print('TDX:', d.get('tdx_enabled'))
print()
for s in d.get('sources', []):
    active_mark = '<-- ACTIVE' if s.get('is_active') else ''
    print(f'{s["name"]:20s} status={s["status"]:10s} {active_mark}')
