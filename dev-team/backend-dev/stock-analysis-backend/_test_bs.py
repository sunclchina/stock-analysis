"""Test baostock"""
import baostock as bs, sys
lg = bs.login()
print(f"Login: {lg.error_code} {lg.error_msg}", flush=True)
if lg.error_code == '0':
    rs = bs.query_all_stock('2026-05-06')
    if rs.error_code == '0':
        cnt = 0
        while rs.next():
            cnt += 1
        print(f"All stocks: {cnt}", flush=True)
    bs.logout()
else:
    print("Login failed", flush=True)
    sys.exit(1)
