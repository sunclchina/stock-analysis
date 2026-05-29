"""Find remaining unmatched backticks"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
bt = 0
for i, line in enumerate(lines):
    bt += line.count(b'\x60')
    if bt % 2 == 1:
        print(f'Line {i+1}: odd ({bt} total)')
        print(f'  {line[:150]}')
        break
