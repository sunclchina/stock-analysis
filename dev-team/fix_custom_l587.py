"""Fix line 587"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
lines[586] = b"    { title: 'Resonance', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,"
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Fixed line 587')
