"""Fix line 334 in FixedSelectionTab.tsx - add missing / >"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b'locale={{ emptyText:' in line:
        # Add /> at the end of the line
        line = line.rstrip(b'\r')
        if not line.rstrip().endswith(b'/>'):
            lines[i] = line + b' />\r'
            print(f'Fixed line {i+1}: added />')
        break
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
