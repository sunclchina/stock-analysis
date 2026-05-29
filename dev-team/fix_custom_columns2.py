"""Fix remaining garbled column definitions in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix specific known problematic lines
for i, line in enumerate(lines):
    # Fix Resonance status column title
    if b"'Resonance Status'" in line and b"resonanceStatus" in line and b"\xe7\x9b\x98" in line:
        lines[i] = b"    { title: 'Resonance', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,"
        print(f'Fixed line {i+1}: Resonance title')
    
    # Fix status.includes garbled text
    if b"status.includes(" in line and b"\xe6\xbe\xb6" in line:
        lines[i] = b'      render: (status: string) => status ? <Tag color={status.includes(\"Up\") ? \"green\" : status.includes(\"Down\") ? \"red\" : \"default\"} style={{ fontSize: 11 }}>{status}</Tag> : <Text type=\"secondary\">-</Text>,'
        print(f'Fixed line {i+1}: status includes')
    
    # Fix any garbled Action column title (dataIndex: "action")
    if b"key: 'action'" in line and b"title:" in line and sum(1 for b in line if b > 127) > 0:
        lines[i] = b"    { title: 'Watchlist', dataIndex: 'action', key: 'action', width: 70, fixed: 'right' as const,"
        print(f'Fixed line {i+1}: action column')
    
    # Fix garbled tooltip for watchlist toggle
    if b"<Tooltip title={record.addedToWatchlist" in line:
        lines[i] = b"        <Tooltip title={record.addedToWatchlist ? 'Remove' : 'Add'}>"
        print(f'Fixed line {i+1}: tooltip')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
