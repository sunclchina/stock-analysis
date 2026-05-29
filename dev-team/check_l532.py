"""Check line 532 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

print(f'Line 532: {lines[531]}')

# Find the function that ends here  
for i in range(515, 535):
    print(f'{i+1}: {lines[i]}')
