"""Test if the disk cache fallback works"""
import json
from pathlib import Path

f = Path("data/a_share_cache/stock_codes.json")
print(f"File path: {f.absolute()}")
print(f"File exists: {f.exists()}")

if f.exists():
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    print(f"beijing total: {d.get('beijing',{}).get('total',0)}")
    print(f"etf total: {d.get('etf',{}).get('total',0)}")
else:
    print("FILE NOT FOUND")
