"""Check and fix line 513 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(510, 520):
    if i < len(lines):
        print(f'{i+1}: {repr(lines[i][:200])}')
