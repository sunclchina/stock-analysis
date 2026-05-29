"""Fix column titles in CustomSelectionTab.tsx around lines 585-640"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Find and fix all garbled column titles
fixes = {
    b'\xe5\x85\xb1\xe6\x8c\xaf\xe7\x8a\xb6\xe6\x80\x81\xe7\x9b\x98?': b'Resonance Status',
    b'\xe7\x93\x92\xe5\x8a\xbf\xe5\x93\x84\xe5\xae\xb3': b'Trend Strength',
    b'\xe9\xa3\x8e\xe9\x99\xa9\xe8\xaf\x84\xe5\x88\x86': b'Risk Score',
    b'\xe9\xa3\x8e\xe9\x99\xa9\xe7\xad\x9b\xe9\xaa\x87': b'Risk Level',
    b'\xe8\xb4\xa2\xe5\x8a\xa1\xe7\xad\x9b\xe9\xaa\x87': b'Finance Grade',
    b'\xe7\xbc\x81\xe7\x85\x8e\xe5\xaf\xb0\xe6\xa5\x80\xe5\x9e\x8e': b'Composite Score',
    b'\xe4\xbd\x8d\xe5\xba\xa8\xee\x97\x93\xe9\x97\x84?': b'Low',
    b'\xe4\xb8\x80\xee\x85\xa2\xee\x97\x93\xe9\x97\x84?': b'Medium',
    b'\xe6\xa5\x82\xe6\xa9\x80\xee\x97\x93\xe9\x97\x84?': b'High',
    b"\xe6\xbe\xb6\xe9\x80\x9a\xe3\x81\x94": b'Long',
    b"\xe7\xbb\x8f\xe5\x93\x84\xe3\x81\x94": b'Short',
}

for i, line in enumerate(lines):
    for garbled, clean in fixes.items():
        if garbled in line:
            lines[i] = line.replace(garbled, clean)
            
# Also fix specific broken quote patterns
for i, line in enumerate(lines):
    # Fix: ,'  at end of line after garbled (unmatched trailing single quote)
    stripped = line
    if b"width: 90,'" in stripped:
        lines[i] = stripped.replace(b"width: 90,'", b"width: 90,")
    if b"width: 85,'" in stripped:
        lines[i] = stripped.replace(b"width: 85,'", b"width: 85,")

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'{len(data)} -> {len(new_data)} bytes')
