"""Fix lines 346 and 364 in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 346 - double >>
data = data.replace(b'label="Resonance">>', b'label="Resonance">')
print('Fixed line 346: double >>')

# Fix line 364 - garbled filter description
old_start = b"    {filterModal === 'L1' ? '"
idx = data.find(old_start)
if idx >= 0:
    # Find the end of this expression - look for "}" after a single-quoted string
    end_idx = data.find(b"'}'\r", idx)
    if end_idx < 0 or end_idx > idx + 500:
        # Try another pattern
        end_idx = data.find(b"}'", idx + 100)
    if end_idx < 0 or end_idx > idx + 500:
        # Search more broadly
        for end_candidate in [b"}'\r", b"'}'\n"]:
            end_idx = data.find(end_candidate, idx)
            if end_idx >= 0 and end_idx < idx + 500:
                break
    
    if end_idx >= 0 and end_idx < idx + 500:
        new_text = b"    {filterModal === 'L1' ? 'L1 removes ST/suspended/low-liq' : filterModal === 'L5' ? 'L5 score>=85 + capacity' : 'See condition list'}"
        data = data[:idx] + new_text + data[end_idx+3:]
        print(f'Fixed line 364: filter description (idx={idx}, end={end_idx})')
    else:
        print(f'Could not find end of line 364 (idx={idx})')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
