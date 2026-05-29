"""Fix line 378 unmatched backtick"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Line 378 (0-indexed 377)
old = lines[377]
# Add closing backtick before );
new = old.replace(b');', b'\x60);')
lines[377] = new
print(f'Fixed line 378: added closing backtick')

# Also fix remaining garbled message calls
for i, line in enumerate(lines):
    if b"message.warning(" in line and sum(1 for b in line if b > 127) > 3:
        lines[i] = b"        message.warning('Results limited to 500, add more conditions')"
        print(f'Fixed line {i+1}: message.warning')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
