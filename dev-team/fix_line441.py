"""Fix line 441 - missing closing brace in if block."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Line 441 (0-indexed 440)
old = lines[440]
print(f'Line 441: {old}')

# Replace with proper code including closing brace
new = b"    if (!d) { message.warning('Invalid template data'); return; }"
lines[440] = new

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Fixed. {len(data)} -> {len(new_data)} bytes')
