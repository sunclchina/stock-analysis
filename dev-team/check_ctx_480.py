"""Check broader context around this useCallback"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Find the useCallback that ends at line 513
for i in range(480, 515):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:200]}')
