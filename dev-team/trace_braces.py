"""Trace brace balance for FixedSelectionTab.tsx lines 200-380"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

depth = 0
for i in range(199, 380):
    if i >= len(lines):
        break
    line = lines[i]
    opens = line.count(b'{')
    closes = line.count(b'}')
    # Adjust for braces inside strings (single-quoted)
    # Count only braces outside strings
    in_single = False
    in_backtick = False
    real_opens = 0
    real_closes = 0
    for b in line:
        if b == 0x27:  # single quote
            in_single = not in_single
        elif b == 0x60:  # backtick
            in_backtick = not in_backtick
        elif b == ord('{') and not in_single and not in_backtick:
            real_opens += 1
        elif b == ord('}') and not in_single and not in_backtick:
            real_closes += 1
    
    depth += real_opens - real_closes
    # Only print when depth changes or key lines
    if abs(real_opens - real_closes) > 0 or i in [259, 260, 268, 269, 330, 334, 360, 362, 364, 371, 372, 375, 376]:
        stripped = line.strip()[:80]
        print(f'{i+1:4d}: d={depth:+d} (o={real_opens}, c={real_closes}) {stripped}')
