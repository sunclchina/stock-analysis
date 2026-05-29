# Simulate what _fetch_a_share_codes_sync does
# 1. Check disk cache - nonexistent (deleted)
# 2. Try akshare stock_info_a_code_name
import akshare as ak
import sys
try:
    df = ak.stock_info_a_code_name()
    print(f'akshare stock_info_a_code_name: {len(df)} stocks')
    print(f'Columns: {df.columns.tolist()}')
    codes = df['code'].tolist()
    print(f'Sample codes: {codes[:5]}')
    
    # Count BJ
    bj = sum(1 for c in codes if str(c).startswith(('920','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873')))
    print(f'BJ count: {bj}')
    
    # Look for BJ codes more broadly
    bj_codes = [c for c in codes if str(c).startswith(('9','4','8'))]
    print(f'Codes starting with 9/4/8: {len(bj_codes)}')
    if bj_codes:
        print(f'Sample: {bj_codes[:15]}')
except Exception as e:
    print(f'akshare failed: {e}')
