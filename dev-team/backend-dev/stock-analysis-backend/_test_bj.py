import httpx, json

# Test beijing stocks
nodes = ['bj_a']
for node in nodes:
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    params = {'page': '1', 'num': '30', 'sort': 'code', 'asc': '1', 'node': node}
    with httpx.Client(timeout=15) as c:
        try:
            r = c.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
            text = r.text.strip()
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]
            data = json.loads(text)
            print(f'{node}: {len(data)} items')
            if data:
                for item in data[:10]:
                    sym = item.get('symbol', '')
                    name = item.get('name', '')
                    code = sym[2:] if sym.startswith(('sh','sz','bj')) else sym
                    print(f'  {code} {name}')
            else:
                print('  EMPTY')
        except Exception as e:
            print(f'{node}: FAILED - {e}')
