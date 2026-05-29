"""Direct fix for line 512."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Line 512 (0-indexed 511)
old_line = lines[511]
print(f'Old line 512: {repr(old_line)}')

# Create new line preserving only the ${tmpl.name} expression
new_line = b"    message.success(`\xe6\xa8\xa1\xe6\x9d\xbf\xe5\x8a\xa0\xe8\xbd\xbd\xe5\xae\x8c\xe6\x88\x90: ${tmpl.name}`);"

# Actually just use English  
new_line = b"    message.success(`Template loaded: ${tmpl.name}`);\r"

lines[511] = new_line
print(f'New line 512: {repr(new_line)}')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Written: {len(data)} -> {len(new_data)} bytes')
