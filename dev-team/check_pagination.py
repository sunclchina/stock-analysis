"""Fix pagination braces"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find the showTotal line
idx = data.find(b'showTotal')
if idx >= 0:
    eol = data.find(b'\n', idx)
    line = data[idx:eol] if eol >= 0 else data[idx:idx+120]
    print(f'ShowTotal line: {repr(line)}')
    
# Fix: ensure pagination structure is correct
# pagination={{ ... }} needs }}
data = data.replace(b'                }}\n                locale', b'                }}\n                locale')

# Actually, find the Pagination section and fix it
# Pattern: showTotal line ends with ` }, and next line is }}
# We need: showTotal line ends with ` and next line is }},
# Or: } at end of showTotal line means }} at next line is extra

# Let me check what we actually have
idx = data.find(b'showTotal: (total, range)')
if idx >= 0:
    after = data[idx+len(b'showTotal: (total, range)'):idx+len(b'showTotal: (total, range)')+120]
    print(f'After showTotal: {repr(after)}')

with open(fp, 'rb') as f:
    pass  # Don't write unless needed
print('Analysis done')
