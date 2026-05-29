import akshare as ak

# Try today's pool
df = ak.stock_zt_pool_em()
if df is not None and not df.empty:
    print(f"今日涨停池: {len(df)} 只")
    print("列:", df.columns.tolist())
    print(df[['代码','名称','涨跌幅','连板数','封板原因']].head(3).to_string())
else:
    print("今日涨停池: 空")

# Try previous day
df2 = ak.stock_zt_pool_previous_em()
if df2 is not None and not df2.empty:
    print(f"\n昨日涨停池: {len(df2)} 只")
    print(df2[['代码','名称','涨跌幅','连板数']].head(3).to_string())
else:
    print("昨日涨停池: 空")

# Try strong pool
df3 = ak.stock_zt_pool_strong_em()
if df3 is not None and not df3.empty:
    print(f"\n强势股池: {len(df3)} 只")
    print(df3[['代码','名称','涨跌幅']].head(3).to_string())
else:
    print("强势股池: 空")
