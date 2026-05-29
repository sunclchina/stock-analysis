"""Check context around line 510-515"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(500, 520):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:200]}')
