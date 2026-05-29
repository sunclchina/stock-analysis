"""Check backtick balance before line 381"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

bt = 0
for i, line in enumerate(lines):
    tick = line.count(b'\x60')
    bt += tick
    if bt % 2 == 1:
        single_q = sum(1 for b in line if b == 0x27)
        print(f'Line {i+1}: odd balance ({bt} total, {single_q} sq)')
        print(f'  {line[:150]}')
        if i >= 380:
            break
