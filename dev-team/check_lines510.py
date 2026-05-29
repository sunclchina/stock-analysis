"""Check lines 510-520 after fixes"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(500, 525):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i]}')
