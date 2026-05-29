"""Fix FixedSelectionTab.tsx Table element - add closing /> and fix locale"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 333: add \r
if not lines[332].endswith(b'\r'):
    lines[332] += b'\r'

# Fix line 334: fix locale and add /> for Table
old334 = b'            locale={{ emptyText: <Empty description="'
idx334 = lines[333].find(old334)
if idx334 >= 0:
    lines[333] = b"            locale={{ emptyText: <Empty description='No stocks matched criteria' /> }} />}\r"
    print(f'Fixed line 334: locale + Table />')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
