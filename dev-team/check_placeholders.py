"""Check and fix ALL placeholder issues in CustomSelectionTab.tsx"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Show all lines with placeholder= that might have issues
print('=== Lines with placeholder= ===')
for i, line in enumerate(lines):
    if b'placeholder=' in line:
        stripped = line.strip()
        sq = [j for j, b in enumerate(stripped) if b == 0x27]
        dq = [j for j, b in enumerate(stripped) if b == 0x22]
        bt = [j for j, b in enumerate(stripped) if b == 0x60]
        all_q = sq + dq + bt
        print(f'Line {i+1}: sq={len(sq)} dq={len(dq)} bt={len(bt)} | {stripped[:100]}')
