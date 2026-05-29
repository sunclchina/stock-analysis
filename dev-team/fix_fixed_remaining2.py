"""Fix remaining garbled text in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 248 - garbled cm dictionary
for i, line in enumerate(lines):
    if b'const cm: Record<string, string> = ' in line:
        lines[i] = b"        const cm: Record<string, string> = { 'Key buy': '#52c41a', 'Normal': '#1677ff', 'Light': '#faad14', 'Skip': '#8c8c8c' };"
        print(f'Fixed line {i+1}: cm dict')

# Fix line 251 - garbled Action column title
for i, line in enumerate(lines):
    if b"key: 'action'" in line and b'width: 70' in line:
        lines[i] = b"    { title: 'Watchlist', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,"
        print(f'Fixed line {i+1}: action column')

# Fix line 253 - garbled tooltip text
for i, line in enumerate(lines):
    if b'<Tooltip title={record.addedToWatchlist' in line:
        lines[i] = b"        <Tooltip title={record.addedToWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}>"
        print(f'Fixed line {i+1}: tooltip')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
