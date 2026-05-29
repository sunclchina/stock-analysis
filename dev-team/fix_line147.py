"""Fix line 147 garbled text"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
# Replace entire line 147 with clean text
lines[146] = b"        message.success('Selection complete');"
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)

# Verify backtick balance
new_bt = 0
for i, line in enumerate(new_data.split(b'\n')):
    new_bt += line.count(b'\x60')
print(f'Fixed line 147. Backtick balance: {new_bt % 2 == 0} ({new_bt} total)')
