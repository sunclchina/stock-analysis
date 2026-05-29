"""Fix remaining issues in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix all missing closures
data = data.replace(b'\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac', b'Done')
data = data.replace(b'Done)\x0d\x0a    const dims', b'Done); return; }\x0d\x0a    const dims')
# But wait - the first occurrence is in handleSaveTemplate, second in handleExport
# Let me reset and do this differently

with open(fp, 'rb') as f:
    data = f.read()

# Find and fix the specific if blocks ONE AT A TIME
# 1. Line 441: if (!d) { message.warning('Done') -> fix
old1 = b"if (!d) { message.warning('Done')\r\n"
new1 = b"if (!d) { message.warning('Done'); return; }\r\n"
data = data.replace(old1, new1)

# 2. Line 517: if (!templateName.trim()) { message.warning('Done') -> fix
old2 = b"if (!templateName.trim()) { message.warning('Done')\r\n"
new2 = b"if (!templateName.trim()) { message.warning('Done'); return; }\r\n"
data = data.replace(old2, new2)

# 3. Line 519: if (Object.keys(dims).length === 0) { message.warning('Done') -> fix  
old3 = b"if (Object.keys(dims).length === 0) { message.warning('Done')\r\n"
new3 = b"if (Object.keys(dims).length === 0) { message.warning('Done'); return; }\r\n"
data = data.replace(old3, new3)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed missing braces')
