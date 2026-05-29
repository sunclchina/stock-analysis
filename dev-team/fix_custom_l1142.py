"""Fix line 1142 in CustomSelectionTab.tsx - garbled showTotal"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 1142 (0-indexed 1141)
lines[1141] = b'                  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total` }},'
print(f'Fixed line 1142: showTotal')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)

# Verify backtick balance
bt = sum(line.count(b'\x60') for line in new_data.split(b'\n'))
print(f'Backtick balance: {bt % 2 == 0} ({bt} total)')
