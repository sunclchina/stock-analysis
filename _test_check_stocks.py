import akshare as ak
import pandas as pd
df = ak.stock_info_a_code_name()
codes = df['code'].astype(str).str.strip().tolist()

# Check some special prefixes
for prefix in ['302', '689', '200', '900', '430', '830', '831']:
    found = [c for c in codes if c.startswith(prefix)]
    if found:
        row = df[df['code'].astype(str).str.strip() == found[0]]
        print(prefix + ": " + found[0] + " -> " + row.iloc[0]["name"] + " (" + str(len(found)) + " total)")
    else:
        print(prefix + ": none found")

print("\nSample codes:", codes[:10])
print("Total:", len(codes))
