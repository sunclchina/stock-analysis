"""Find extra braces in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Find component close patterns
for i, line in enumerate(lines):
    s = line.strip()
    if s == b'};':
        print(f'Line {i+1}: component close')
    if s == b'}':
        print(f'Line {i+1}: standalone brace')
    # Check for } at end that might be not paired with { at start
    if s and s[-1:] == b'}':
        opens = line.count(b'{')
        closes = line.count(b'}')
        if opens == 0 and closes > 0:
            print(f'Line {i+1}: only closes, no opens: {line[:80]}')
