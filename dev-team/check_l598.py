"""Check column definitions in CustomSelectionTab.tsx around line 598"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(590, 630):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}')
