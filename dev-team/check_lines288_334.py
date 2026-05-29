"""Check lines 287-289 and 332-335"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

print('=== Lines 286-290 ===')
for i in range(285, 291):
    print(f'{i+1}: {lines[i]}')

print()
print('=== Lines 330-338 ===')
for i in range(329, 339):
    print(f'{i+1}: {lines[i]}')
