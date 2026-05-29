"""Full brace balance from the start of FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

depth = 0
# Track brace balance
imbalance = []
for i, line in enumerate(lines):
    opens = line.count(b'{')
    closes = line.count(b'}')
    depth += opens - closes
    imbalance.append((i+1, depth, opens, closes, line.strip()[:80]))

# Find where imbalance starts
print(f'Final depth: {depth}')
print(f'Lines with net nonzero:')
for ln, d, o, c, text in imbalance:
    if o != c:
        print(f'  Line {ln}: d={d:+d} o={o} c={c} | {text}')
