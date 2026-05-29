"""Fix line 333 garbled template literal"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 333 (0-indexed 332)
old = lines[332]
# Replace the garbled content between backtick and }}
new = b"                showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` }}"
lines[332] = new
print(f'Fixed line 333: {old[:60]} -> {new[:60]}')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)

# Verify backtick balance
bt = sum(line.count(b'\x60') for line in new_data.split(b'\n'))
print(f'Backtick balance: {bt % 2 == 0} ({bt} total)')
