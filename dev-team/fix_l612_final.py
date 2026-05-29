"""Fix line 612 - garbled ll dictionary"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
lines[611] = b"        const ll: Record<string, string> = { low: 'Low', medium: 'Medium', high: 'High' };"
with open(fp, 'wb') as f:
    f.write(b'\n'.join(lines))
print('Fixed line 612')
