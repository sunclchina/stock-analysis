"""Fix garbled text in FixedSelectionTab.tsx lines 186, 192, 195"""
import sys

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 186: garbled ternary values
if 185 < len(lines):
    old = lines[185]
    sq = old.count(b"'")
    print(f'Line 186: {sq} single quotes')
    # Find the garbled part and replace
    if b'\xe9\x8f\x84' in old:
        lines[185] = old[:185] + b"r.addedToWatchlist ? 'Yes' : 'No']);" 
    # Actually, just replace the garbled ternary
    idx = old.find(b"? '")
    if idx > 0:
        # Find the garbled text after ?
        lines[185] = old[:idx] + b"? 'Yes' : 'No']);"
        print(f'Fixed line 186: ternary')

# Fix line 192: garbled download filename
if 191 < len(lines):
    old = lines[191]
    if b'\xe9\x80\x89\xe8' in old:
        # Replace the download string
        idx = old.find(b'.download')
        if idx > 0:
            lines[191] = old[:idx] + b".download = `selection_${strategies[selectedStrategy]?.label || 'fixed'}_${new Date().toISOString().slice(0, 10)}.csv`;"
            print(f'Fixed line 192: download filename')

# Fix line 195: garbled success message
if 194 < len(lines):
    old = lines[194]
    if b'\xe7\x80\xb5' in old:
        lines[194] = b"    message.success('Export successful');"
        print(f'Fixed line 195: success message')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
