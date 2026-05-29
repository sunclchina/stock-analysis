"""Fix garbled Descriptions labels in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find and replace garbled Descriptions labels
replacements = [
    (b'label="\xe4\xbb\xb7\xe9\x94\x8b\xe7\x89\xb8"', b'label="Price"'),
    (b'label="\xe5\xa8\x91\xe3\x84\xa8\xe7\xa9\xbc\xe9\xaa\x9e?>', b'label="Change">'),
    (b'label="\xe7\xbc\x81\xe7\x85\x8e\xe5\xaf\xb0\xe6\xa5\x80\xe5\x9e\x8e"', b'label="Composite"'),
    (b'label="\xe9\xa3\x8e\xe9\x99\xa9\xe8\xaf\x84\xe5\x88\x86"', b'label="Risk Score"'),
    (b'label="\xe9\xa3\x8e\xe9\x99\xa9\xe7\xad\x9b\xe9\xaa\x87"', b'label="Risk Level"'),
    (b'label="\xe7\x93\x92\xe5\x8a\xbf\xe5\x93\x84\xe5\xae\xb3"', b'label="Trend"'),
    (b'label="\xe5\x85\xb1\xe6\x8c\xaf\xe7\x8a\xb6\xe6\x80\x81\xe7\x9b\x98?', b'label="Resonance">'),
    (b'label="\xe8\xb4\xa2\xe5\x8a\xa1\xe7\xad\x9b\xe9\xaa\x87"', b'label="Fin Grade"'),
    (b'label="\xe9\x8e\xbf\xe5\xb6\x84\xe7\xb6\x94\xe5\xaf\xa4\xe9\xb8\xbf\xee\x86\x85"', b'label="Advice"'),
]

for old, new in replacements:
    if old in data:
        data = data.replace(old, new)
        print(f'Fixed: {repr(old[:30])}')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
