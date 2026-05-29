"""Check line 364"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

line = lines[363]
print('Line 364:', repr(line))
print()
ticks = line.count(b'\x60')
sq = line.count(b"'")
print(f'Backticks: {ticks}')
print(f'Single quotes: {sq}')
print(f'Length: {len(line)}')
