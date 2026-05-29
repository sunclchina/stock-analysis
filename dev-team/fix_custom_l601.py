"""Fix line 601"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
lines[600] = b"        const ll: Record<string, string> = { low: 'Low', medium: 'Medium', high: 'High' };"
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Fixed line 601')
