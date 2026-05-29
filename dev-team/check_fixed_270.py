"""Check FixedSelectionTab.tsx around lines 270-315."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(269, 340):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i]}')
