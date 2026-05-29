"""Fix line 598's title attribute"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find and fix the line with 'Resonance Status, dataIndex:' (broken title string)
old = b"'Resonance Status, dataIndex: '"
new = b"'Resonance Status'"
data = data.replace(old, new)

with open(fp, 'wb') as f:
    f.write(data)
print(f'Fixed: replaced "{old}" with "{new}"')
