import akshare as ak
import pandas as pd

# Try to get ALL stocks including BJ from akshare
print("=== stock_zh_a_spot columns ===")
df = ak.stock_zh_a_spot()
print(f'Total: {len(df)} stocks')
# check codes for beijing (92xxxx, 43xxxx, 83xxxx etc)
bj_count = 0
codes = df['代码'].tolist()
for c in codes:
    cs = str(c)
    if cs.startswith(('920','430','830','831','832','833','834','835','836','837','838','839','870','871','872','873')):
        bj_count += 1
print(f'Beijing stocks in spot: {bj_count}')

# Check ETF counts
etf_sh = sum(1 for c in codes if str(c).startswith(('51','52','56','58')))
etf_sz = sum(1 for c in codes if str(c).startswith('159'))
print(f'ETF: SH={etf_sh}, SZ={etf_sz}')
print(f'Sample BJ codes: {[c for c in codes[:200] if str(c).startswith(("9","4","8"))][:10]}')
