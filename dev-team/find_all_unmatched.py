"""Find ALL unmatched backticks in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

bt = 0
for i, line in enumerate(lines):
    tick_count = line.count(b'\x60')
    bt += tick_count
    if bt % 2 == 1:
        print(f'Line {i+1}: odd balance ({bt} total, {tick_count} on this line)')
        print(f'  {line[:150]}')
