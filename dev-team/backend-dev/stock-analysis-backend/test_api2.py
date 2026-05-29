import httpx
r = httpx.get('http://127.0.0.1:8000/api/v1/market/quotes/300850,600666', timeout=10)
d = r.json()
count = d.get('count')
source = d.get('active_data_source')
print(f'count={count}, source={source}')
for q in d.get('quotes', []):
    code = q.get('code', '?')
    name = q.get('name', '?')
    price = q.get('price', '?')
    print(f'  {code} {name} {price}')
