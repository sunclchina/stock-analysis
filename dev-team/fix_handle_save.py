"""Fix handleSaveTemplate braces"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Fix line 517
lines[516] = b"    if (!templateName.trim()) { message.warning('Enter template name'); return; }"

# Fix line 519
lines[518] = b"    if (Object.keys(dims).length === 0) { message.warning('No conditions configured'); return; }"

# Fix line 529
lines[528] = b"    message.success('Template saved');"

with open(fp, 'wb') as f:
    f.write(b'\n'.join(lines))
print('Fixed')
