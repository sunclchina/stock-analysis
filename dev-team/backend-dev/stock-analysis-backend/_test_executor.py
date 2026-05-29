"""Test akshare in thread pool"""
import asyncio, sys, akshare as ak

async def main():
    print("Testing akshare stock_info_a_code_name in executor...")
    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, ak.stock_info_a_code_name)
        print(f"Success: {len(df)} stocks")
        codes = df['code'].tolist()
        bj = sum(1 for c in codes if str(c).startswith(
            ("920","430","830","831","832","833","834","835","836","837","838","839","870","871","872","873")))
        print(f"BJ count: {bj}")
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

    print("Testing fund_etf_spot_em in executor...")
    try:
        loop = asyncio.get_event_loop()
        etf = await loop.run_in_executor(None, ak.fund_etf_spot_em)
        if etf is not None and not etf.empty:
            esh = sum(1 for c in etf['代码'].tolist() if str(c).startswith(("51","52","56","58")))
            esz = sum(1 for c in etf['代码'].tolist() if str(c).startswith("159"))
            print(f"ETF: SH={esh} SZ={esz}")
        else:
            print("ETF: empty result")
    except Exception as e:
        print(f"ETF FAILED: {e}", file=sys.stderr)

asyncio.run(main())
