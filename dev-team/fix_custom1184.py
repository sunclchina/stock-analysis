"""Fix line 1184 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
lines[1183] = b'                          {tmpl.max_results ? ` (${tmpl.max_results} items)` : chr(34)+chr(34)}'
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
bt = sum(x.count(b'\x60') for x in new_data.split(b'\n'))
print(f'Fixed. Backtick balance: {bt % 2 == 0} ({bt} total)')
