"""Fix line 364 completely"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
new_line = b"            {filterModal === 'L1' ? 'L1: basic filters' : filterModal === 'L5' ? 'L5: score 85+' : 'View conditions'}"
lines[363] = new_line
with open(fp, 'wb') as f:
    f.write(new_data if 'new_data' in dir() else b'')
    f.write(b'\n'.join(lines))
print('Fixed line 364')
