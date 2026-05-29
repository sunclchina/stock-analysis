"""Fix lines 346 and 364"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 346: double >>
data = data.replace(b'Resonance">>', b'Resonance">')

# Fix line 364: garbled filter text in ternary
# Find the ternary text at line 364
for old, new in [
    (b"L1 removes ST/suspended/low-liq", b"L1 removes problem stocks"),
    (b"L5 score>=85 + capacity", b"L5 score >= 85"),
]:
    data = data.replace(old, new)

# Also fix trailing issue
data = data.replace(b": 'L1 removes problem stocks' : filterModal === 'L5' ? 'L5 score >= 85' : 'See condition list'", 
                     b": 'L1: basic filters' : filterModal === 'L5' ? 'L5: score >= 85, capacity control' : 'See condition list'")

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
