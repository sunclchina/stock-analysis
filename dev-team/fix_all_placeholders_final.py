"""Fix ALL placeholder closing quotes in CustomSelectionTab.tsx comprehensively"""
import sys

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')
fix_count = 0

for i, line in enumerate(lines):
    if b'placeholder=' not in line:
        continue
    
    # Find all placeholder="..." patterns
    idx = 0
    while True:
        idx = line.find(b'placeholder=', idx)
        if idx < 0:
            break
        
        # Find the opening quote
        open_q = idx + 12
        if open_q >= len(line) or line[open_q:open_q+1] not in [b'"', b"'"]:
            idx = open_q
            continue
        
        qchar = line[open_q:open_q+1]  # " or '
        
        # Find the matching close quote
        rest = line[open_q+1:]
        close_q = rest.find(qchar)
        
        if close_q < 0:
            # No closing quote found on this line
            # Check if it ends with \r 
            eol = line[-1:]
            # Add closing quote before EOL
            lines[i] = line[:open_q+1] + rest.rstrip() + qchar + eol
            fix_count += 1
            break
        
        idx = open_q + close_q + 2

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Fixed {fix_count} unclosed placeholder strings')
