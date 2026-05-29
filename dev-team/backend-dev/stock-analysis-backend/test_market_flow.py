import httpx

# 1. Monitoring pool
r = httpx.get('http://127.0.0.1:8000/api/v1/market/quotes', timeout=10)
d = r.json()
count = d.get('count', 0)
source = d.get('active_data_source', '?')
codes = d.get('codes', [])
print('Monitoring pool: count=%d, source=%s' % (count, source))
print('Codes (%d): %s...' % (len(codes), ','.join(codes[:5])))
for q in d.get('quotes', []):
    code = q.get('code', '?')
    name = q.get('name', '?')
    price = q.get('price')
    note = q.get('note', '')
    print('  %s %s price=%s note=%s' % (code, name, price, note))
if count == 0:
    print('  EMPTY - no data!')

print()

# 2. Test specific stocks
r2 = httpx.get('http://127.0.0.1:8000/api/v1/market/quotes/300850,600666,300207,600501', timeout=10)
d2 = r2.json()
c2 = d2.get('count')
s2 = d2.get('active_data_source', '?')
print('Specific quotes: count=%d, source=%s' % (c2, s2))
for q in d2.get('quotes', []):
    print('  %s %s price=%s' % (q.get('code'), q.get('name'), q.get('price')))
