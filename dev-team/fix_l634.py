"""Fix line 634"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
lines[633] = b"    { title: 'Watchlist', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,"
# Also fix tooltip to have different text
lines[635] = b"        <Tooltip title={record.addedToWatchlist ? 'Remove' : 'Add'}>"
with open(fp, 'wb') as f:
    f.write(b'\n'.join(lines))
print('Fixed line 634 and 636')
