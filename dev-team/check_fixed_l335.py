"""Check line 335 in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(330, 340):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}')
