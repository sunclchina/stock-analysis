"""Quick fix for all remaining garbled text in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix specific garbled lines with unmatched backticks
fixes = {
    # Line 382: message.info with garbled template
    381: b"        message.info(`Selected ${items.length} stocks, consider adding more criteria`);",
    # Line 384: message.success with garbled template  
    383: b"        message.success(`Selection complete: ${items.length} stocks found`);",
}

for line_num, content in fixes.items():
    idx = line_num - 1  # 0-indexed
    if idx < len(lines):
        old = lines[idx]
        lines[idx] = content
        print(f'Fixed line {line_num}: {old[:50]} -> {content[:50]}')

# Also fix the download filename line
for i, line in enumerate(lines):
    if b'a.download =' in line and sum(1 for b in line if b > 127) > 0:
        lines[i] = b"    a.download = `selection_results_${new Date().toISOString().slice(0, 10)}.csv`;"
        print(f'Fixed line {i+1}: download filename')

# Verify backtick balance
new_data = b'\n'.join(lines)
bt = sum(line.count(b'\x60') for line in new_data.split(b'\n'))
print(f'Backtick balance: {bt % 2 == 0} ({bt} total)')

with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
