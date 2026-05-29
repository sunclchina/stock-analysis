"""Check the handleLoadTemplate function opening."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
for i in range(438, 470):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:200]}')
