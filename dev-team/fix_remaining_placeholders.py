"""Fix remaining placeholder issues"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix specific lines with double-quote or garbled placeholder issues
fixes = [
    (b'placeholder="\xe9\x88\xae?"', b'placeholder="min"'),
    (b'placeholder="\xe9\x88\xae""', b'placeholder="min"'),
    (b'placeholder="\xe4\xb8\x80\xe5\xb6\x88\xe4\xbb\x88\xe9\x8d\x94""', b'placeholder="Enter"'),
    (b'placeholder="\xe6\xb8\x9a\xee\x9b\xa7\xe6\xb0\xad\xe5\x9e\x9c\xe7\x9a\x84\xe5\x8b\xad\xe7\x85\xad\xe7\xbb\xbe\xe6\x8c\x8e\xc4\x81\xe6\x9d\xa1""', b'placeholder="Filter keyword"'),
]

for old, new in fixes:
    if old in data:
        data = data.replace(old, new)
        print(f'Fixed: {old[:20]}')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
