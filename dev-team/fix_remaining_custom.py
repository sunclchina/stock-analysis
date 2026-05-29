"""Fix remaining garbled lines in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix 1: Line 383 - message.info missing backtick  
data = data.replace(
    b'message.info(Found  results);',
    b'message.info(`Found ${items.length} results`);'
)

# Fix 2: Line 385 - message.success missing ${items.length}
data = data.replace(
    b'message.success(`Selection complete:  stocks passed filtering`);',
    b'message.success(`Selection complete: ${items.length} stocks passed filtering`);'
)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
