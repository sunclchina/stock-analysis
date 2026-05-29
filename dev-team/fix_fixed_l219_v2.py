"""Fix garbled text in FixedSelectionTab.tsx around lines 219-224"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 219: garbled column title
lines[218] = b"    { title: 'Resonance', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,"

# Fix line 222: garbled status includes
lines[221] = b'        return <Tag color={status.includes(\'Up\') ? \'green\' : status.includes(\'Down\') ? \'red\' : \'default\'} style={{ fontSize: 11 }}>{status}</Tag>;\r'

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Fixed')
