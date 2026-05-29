"""Check and fix line 376"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(370, 380):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i]}')
