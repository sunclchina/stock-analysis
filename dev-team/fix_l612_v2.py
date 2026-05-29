"""Fix line 612 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b'const ll:' in line and b'low:' in line:
        before = line[:line.find(b'const ll:')]
        after = b'};'
        lines[i] = before + b"const ll: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff4d4f' };"
        # or just use hex color codes without labels since these are the tag colors
        lines[i] = b"        const ll: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff4d4f' };"
        print(f'Fixed line {i+1}')
        break
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
