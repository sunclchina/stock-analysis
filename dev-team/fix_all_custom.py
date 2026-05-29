"""Fix ALL garbled content in CustomSelectionTab.tsx by replacing garbled sections with clean code."""

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Fix the handleExport function (around line 424-430)
for i, line in enumerate(lines):
    # Fix: if (results.length === 0) { message.warning('garbled')
    if b"if (results.length === 0) { message.warning(" in line and b'\x27' in line:
        lines[i] = b'      if (results.length === 0) { message.warning("No data to export"); return; }'
        print(f'Fixed line {i+1}: message.warning in handleExport')
    
    # Fix: const headers = ['garbled', ...]
    if b"const headers = [" in line and b'\xe9\x96\xb9' in line:
        lines[i] = b"      const headers = ['Rank', 'Code', 'Name', 'Industry', 'Trend', 'Resonance', 'Strength', 'Risk Score', 'Risk Level', 'Finance', 'Composite', 'Advice'];"
        print(f'Fixed line {i+1}: headers array')
    
    # Fix: console.error('garbled')
    if b"console.error(" in line and b'\xe6\xbe\xb6' in line:
        lines[i] = line.replace(b'\xe9\x80\x89\xe8\x82\xa1\xe9\xbb\xb7\xe7\x8e\x89\xe8\x9b\xb9\xe9\x81\x8e', b'Custom selection').replace(b'\xe8\x87\xaa\xe5\xae\x9a\xe4\xb9\x89\xe9\xbb\xb7\xe7\x9b\x98\xe8\x82\xa1\xe6\xbe\xb6\xe8\xbe\xab\xe8\xa7\xa6', b'Custom selection error').replace(b'\xe5\x9b\xba\xe5\xae\x9a\xe8\xa7\x84\xe5\x88\x99\xe9\x80\x89\xe8\x82\xa1\xe6\xbe\xb6\xe8\xbe\xab\xe8\xa7\xa6', b'Fixed selection error')
        print(f'Fixed line {i+1}: console.error')

# Fix showTotal in pagination
for i, line in enumerate(lines):
    if b'showTotal:' in line and b'\x60' in line:
        # Check if it has garbled text
        if sum(1 for b in line if b > 127) > 0:
            # Normal pagination showTotal, just clean it
            # Find the showTotal assignment
            start = line.find(b'showTotal:')
            # Replace from showTotal to the comma
            if b'\x24{' in line:
                lines[i] = b'                  showTotal: (total, range) => `${range[0]}-${range[1]} / ${total} total`,'
                print(f'Fixed line {i+1}: showTotal in pagination')

# Fix download filename in handleExport
for i, line in enumerate(lines):
    if b'a.download' in line and b'\x60' in line:
        if sum(1 for b in line if b > 127) > 0:
            lines[i] = b'    a.download = `selection_${new Date().toISOString().slice(0, 10)}.csv`;'
            print(f'Fixed line {i+1}: download filename')

# Fix handleExport fileName with garbled
for i, line in enumerate(lines):
    if b'a.download =' in line and b'\xe9\x80\x89' in line:
        lines[i] = b'    a.download = `selection_results_${strategies[selectedStrategy]?.label || "custom"}_${new Date().toISOString().slice(0, 10)}.csv`;'
        print(f'Fixed line {i+1}: download filename')

# Write back
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'\nWritten: {len(data)} -> {len(new_data)} bytes')

# Check remaining issues
lines2 = new_data.split(b'\n')
unmatched = 0
garbled = 0
for i, line in enumerate(lines2):
    ticks = [j for j, b in enumerate(line) if b == 0x60]
    if len(ticks) % 2 == 1:
        print(f'  UNMATCHED TICK: Line {i+1}: {line[:100]}')
        unmatched += 1
    # Check for high bytes in odd contexts
    if b"'\\x" in line or (line.count(b'\x27') > 0 and sum(1 for b in line if b > 127) > 0):
        # Check if the garbled text is just in string content (which is OK)
        pass

print(f'Remaining issues: {unmatched} unmatched ticks')
