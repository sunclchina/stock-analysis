"""Fix line 195 and garbled column titles"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 195: add \r
lines[194] = b"    message.success('Export successful');\r"

# Fix garbled column titles
for i, line in enumerate(lines):
    for garbled, clean in [
        (b'\xe9\x8e\xba\xe6\x8e\x91\xe6\x82\x95', b'Rank'),
        (b'\xe4\xbb\xb7\xef\xbd\x87\xe7\x88\x9c', b'Code'),
    ]:
        if garbled in line and b"title: '" in line:
            lines[i] = line.replace(garbled, clean)

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Fixed')
