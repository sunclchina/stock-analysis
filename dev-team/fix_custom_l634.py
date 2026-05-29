"""Fix lines 634 and 636 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 634: garbled title and trailing quote
new634 = b"    { title: 'Watchlist', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,\r\n"
# Find the line with 'action' in column definition
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b"width: 70, fixed: 'right' as const" in line:
        lines[i] = b"    { title: 'Watchlist', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,"
        print(f'Fixed line {i+1}')
        break

# Fix line 636: garbled tooltip text
for i, line in enumerate(lines):
    if b"record.addedToWatchlist ? " in line and b'Tooltip' in line:
        lines[i] = b"        <Tooltip title={record.addedToWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}>"
        print(f'Fixed line {i+1}')
        break

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
