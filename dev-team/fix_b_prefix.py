# -*- coding: utf-8 -*-
"""Fix b-prefix in message.warning calls"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b'message.warning(b' in line:
        new = line.replace(b'message.warning(b"Enter name")', b'message.warning("Enter name")')
        new = new.replace(b'message.warning(b"No conditions")', b'message.warning("No conditions")')
        lines[i] = new
        print(f'Fixed line {i+1}')
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
