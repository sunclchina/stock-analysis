import pandas as pd
import httpx, json, math

# Approach 1: akshare stock_info_a_code_name
try:
    import akshare as ak
    df = ak.stock_info_a_code_name()
    print(f'akshare stock_info_a_code_name: {len(df)} stocks')
    codes = df['code'].tolist()
    bj = sum(1 for c in codes if str(c).startswith(('920','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873')))
    etf_sh = sum(1 for c in codes if str(c).startswith(('51','52','56','58')))
    etf_sz = sum(1 for c in codes if str(c).startswith('159'))
    print(f'  北交所: {bj}, ETF_SH: {etf_sh}, ETF_SZ: {etf_sz}')
except Exception as e:
    print(f'akshare stock_info_a_code_name failed: {e}')

# Approach 2: East Money push2 with filters for BJ and ETF
print('\n--- East Money push2 ---')
url = 'https://push2.eastmoney.com/api/qt/clist/get'

# BJ market
params_bj = {
    'pn': '1', 'pz': '5000', 'po': '1', 'np': '1',
    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
    'fltt': '2', 'invt': '2', 'fid': 'f3',
    'fs': 'm:0+t:82',  # 北交所
    'fields': 'f12',
}
with httpx.Client(timeout=30) as c:
    try:
        r = c.get(url, params=params_bj, headers={'User-Agent': 'Mozilla/5.0'})
        d = r.json()
        total_bj = d.get('data', {}).get('total', 0)
        diff_bj = d.get('data', {}).get('diff', [])
        bj_codes = [i.get('f12','') for i in diff_bj]
        print(f'北交所 (m:0+t:82): total={total_bj}, fetched={len(bj_codes)}')
    except Exception as e:
        print(f'BJ failed: {e}')

# ETF market  
params_etf = {
    'pn': '1', 'pz': '5000', 'po': '1', 'np': '1',
    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
    'fltt': '2', 'invt': '2', 'fid': 'f3',
    'fs': 'm:0+t:3',  # 基金(ETF)
    'fields': 'f12',
}
with httpx.Client(timeout=30) as c:
    try:
        r = c.get(url, params=params_etf, headers={'User-Agent': 'Mozilla/5.0'})
        d = r.json()
        total_etf = d.get('data', {}).get('total', 0)
        diff_etf = d.get('data', {}).get('diff', [])
        etf_codes = [i.get('f12','') for i in diff_etf]
        # Count by prefix
        etf_sh = sum(1 for c in etf_codes if str(c).startswith(('51','52','56','58')))
        etf_sz = sum(1 for c in etf_codes if str(c).startswith('159'))
        print(f'ETF (m:0+t:3): total={total_etf}, fetched={len(etf_codes)}')
        print(f'  沪ETF: {etf_sh}, 深ETF: {etf_sz}')
    except Exception as e:
        print(f'ETF failed: {e}')
