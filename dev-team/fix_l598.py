"""Fix lines 598 and 599"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 598: title string missing close quote
data = data.replace(
    b"'Resonance Status, dataIndex: 'resonanceStatus'",
    b"'Resonance Status', dataIndex: 'resonanceStatus'"
)

# Fix line 599: garbled status.includes
data = data.replace(
    b"status.includes('\xe7\xbb\x8f\xe5\x93\x84\xe3\x81\x94')",
    b"status.includes('Down')"
)

# Also fix trailing quote on line 598
data = data.replace(b"width: 90,'", b"width: 90,")

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
