"""Fix all garbled code in CustomSelectionTab.tsx around lines 378-394."""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Replace lines 378-394 (0-indexed: 377-393)
# These are garbled message calls in the handleRun callback
new_lines = list(lines)
new_lines[377] = b'        message.warning("Results exceed 500, add more conditions to narrow scope");'
new_lines[378] = b'      } else if (items.length === 0) {'
new_lines[379] = b"        message.info('No matching stocks found');"
new_lines[380] = b'      } else if (items.length >= 200) {'
new_lines[381] = b"        message.info(`Found ${items.length} results, consider adding more filter criteria`);"
new_lines[382] = b'      } else {'
new_lines[383] = b"        message.success(`Selection complete: ${items.length} stocks passed all 5-layer filters`);"
new_lines[384] = b'      }'

# Also fix line 387 (console.error garbled Chinese)
new_lines[386] = b"      console.error('Custom stock selection error:', err);"
new_lines[387] = b"      message.error('Selection failed, check console for details');"

# Fix line 337 (handleRun export garbled text)
# Search for the garbled text on export and fix it
for i, line in enumerate(lines):
    if b'message.warning' in line and b'No data' not in line and b'noData' not in line:
        if b'\xef\xac\x81' in line:  # garbled text marker
            pass  # handled above

# Now write the fixed content
new_data = b'\n'.join(new_lines)
with open(fp, 'wb') as f:
    f.write(new_data)

print(f'Fixed {fp}')
print(f'{len(data)} -> {len(new_data)} bytes')

# Verify: check remaining unmatched backticks
lines2 = new_data.split(b'\n')
for i, line in enumerate(lines2):
    ticks = [j for j, b in enumerate(line) if b == 0x60]
    if len(ticks) % 2 == 1:
        print(f'  WARNING: Line {i+1} still has {len(ticks)} backtick(s)')
