"""Search for useCallback that ends at line 513."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')
# Search for useCallback in surrounding area
for i in range(400, 515):
    if b'useCallback' in lines[i]:
        print(f'{i+1}: {lines[i][:200]}')
