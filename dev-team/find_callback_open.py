"""Find the opening of the useCallback that ends at line 513."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Find useCallback opening
# The one ending at line 513 is the handleLoadTemplate callback
for i in range(440, 515):
    if i < len(lines):
        line = lines[i].strip()
        if b'const handleLoadTemplate' in line or b'useCallback' in line:
            print(f'{i+1}: {lines[i][:200]}')

# Also specifically find the handleLoadTemplate function
for i in range(440, 515):
    if i < len(lines):
        if b'handleLoadTemplate' in lines[i]:
            print(f'{i+1}: {lines[i][:200]}')
