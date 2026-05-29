"""Fix garbled text in dimension config area of CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Print lines 660-680
for i in range(655, 685):
    if i < len(lines):
        print(f'{i+1:4d}: {lines[i][:180]}')

# Check for lines with garbled bytes
print()
print('=== Lines with high-bit bytes ===')
for i in range(650, 850):
    if i < len(lines):
        if sum(1 for b in lines[i] if b > 127) > 5:
            print(f'{i+1}: {lines[i][:200]}')
