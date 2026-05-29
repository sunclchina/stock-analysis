import httpx, json

# Test East Money push2 directly
url = 'https://push2.eastmoney.com/api/qt/clist/get'
params = {
    'pn': '1', 'pz': '5000', 'po': '1', 'np': '1',
    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
    'fltt': '2', 'invt': '2', 'fid': 'f3',
    'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81,m:0 t:82',
    'fields': 'f12,f14',
}
with httpx.Client(timeout=30) as c:
    r = c.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'})
    d = r.json()
    diff = d.get('data', {}).get('diff', [])
    codes = [i['f12'] for i in diff]
    names = [(i['f12'], i.get('f14','')) for i in diff]
    
    # Count by prefix
    bj = sum(1 for c in codes if str(c).startswith(('920','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873')))
    etf_sh = sum(1 for c in codes if str(c).startswith(('51','52','56','58')))
    etf_sz = sum(1 for c in codes if str(c).startswith('159'))
    print(f'Total: {len(codes)}')
    print(f'BJ: {bj}')
    print(f'ETF SH: {etf_sh}, SZ: {etf_sz}')
    
    # Show some BJ stocks
    print(f'\nSample BJ stocks:')
    for code, name in names:
        if str(code).startswith(('920','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873')):
            print(f'  {code} {name}')
