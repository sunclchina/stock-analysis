"""Fix line 612 in CustomSelectionTab.tsx - garbled risk level labels"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find the garbled line and replace it  
old = b"const ll: Record<string, string> = { low: '"

# Search for the old pattern in various forms
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b'const ll:' in line and b'low:' in line and sum(1 for b in line if b > 127) > 0:
        lines[i] = b'        const ll: Record<string, string> = { low: '#52c41a', medium: '#faad14', high: '#ff4d4f' };'
        print(f'Fixed line {i+1}')
        if b'\x27' in line:
            lines[i] = b'        const ll: Record<string, string> = { low: ' + b"'#52c41a'" + b', medium: ' + b"'#faad14'" + b', high: ' + b"'#ff4d4f'" + b' };'
        break

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
