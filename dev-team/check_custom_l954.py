"""Check specific lines 950-965 and 1020-1035"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
print('=== Lines 950-965 ===')
for i in range(949, 966):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:200]}')
print()
print('=== Lines 1020-1035 ===')
for i in range(1019, 1036):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:200]}')
