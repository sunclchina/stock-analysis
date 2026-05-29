import httpx, json

nodes = ['hs_f', 'sh_f', 'sz_f', 'sh_etf', 'sz_etf']
for node in nodes:
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData'
    params = {'page': '1', 'num': '10', 'sort': 'code', 'asc': '1', 'node': node}
    with httpx.Client(timeout=15) as c:
        try:
            r = c.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
            text = r.text.strip()
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]
            data = json.loads(text)
            print(f'{node}: {len(data)} items')
            if data:
                for item in data[:3]:
                    sym = item.get('symbol', '')
                    print(f'  sym={sym}')
        except Exception as e:
            print(f'{node}: FAILED - {e}')
