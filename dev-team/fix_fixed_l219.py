"""Fix garbled column title line 219"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix the garbled column title
old = b"'Resonance Status\xe7\x9b\x98?, dataIndex: 'resonanceStatus'"
new = b"'Resonance Status', dataIndex: 'resonanceStatus'"
if old in data:
    data = data.replace(old, new)
    print('Fixed column title')
else:
    print('Pattern not found, searching...')
    idx = data.find(b'Resonance Status')
    if idx >= 0:
        print(f'Found at {idx}: {data[idx:idx+80]}')

with open(fp, 'wb') as f:
    f.write(data)
