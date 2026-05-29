"""Fix broken JSX and garbled text in FixedSelectionTab.tsx - targeted fixes."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix all specific broken patterns  
fixes = [
    # Line 272: broken closing tag
    (b'\\xe9\\x80\\x89\\xe8\\x82\\xa1\\xe7\\xad\\x9b\\xe6\\xa0\\xab\\xe6\\x9a\\x90?/Text>', b'Selection Strategy</Text>'),
    
    # Line 288: garbled L0 tag with template
    (b'L0: \\xe9\\x8d\\x8f\\xcb\\x8b\\xe9\\x91\\xb2\\xee\\x94\\x81totalStockCount ? ` (${totalStockCount.toLocaleString()})` :', b'L0: All A-shares{totalStockCount ? ` (${totalStockCount.toLocaleString()})` :'),
    
    # Line 303: garbled comparison string
    (b"'\\xe7\\x9b\\x98\\xe6\\xa8\\xb9\\xe4\\xb8\\xad\\xe5\\xae\\x9e\\xe6\\x97\\xb6'", b"'Trading'"),
    
    # Line 311: broken closing tag
    (b'\\xe6\\x9d\\x88\\xe6\\x92\\xb3\\xe5\\x9a\\xad\\xe4\\xb8\\x80\\xe5\\xa9\\x87\\xe6\\xaa\\xba?/Text>', b'Capacity</Text>'),
    
    # Line 314: broken closing tag  
    (b'\\xe5\\x8f\\x96?/Text>', b'Stocks</Text>'),
    
    # Line 316: garbled button text
    (b'\\xe4\\xb8\\x80\\xe7\\x9b\\x98\\xe9\\x96\\xbf\\xee\\x86\\xbf\\xe7\\xb9\\x8d\\xe7\\x90\\x9b\\xe7\\x9b\\x98\\xe8\\x82\\xa1', b'Run Selection'),
    
    # Line 324: garbled title text and broken tag
    (b'\\xe9\\x80\\x89\\xe8\\x82\\xa1\\xe7\\xbc\\x81\\xe6\\x92\\xb4\\xe7\\x81\\x89', b'Selection Results'),
    (b'\\xe5\\x8f\\x96?/Tag>', b'selected</Tag>'),
    
    # Line 327: garbled button text
    (b'\\xe7\\x80\\xb5\\xe7\\x85\\x8e\\xe5\\x9a\\xadCSV', b'Export CSV'),
    
    # Line 328: garbled button text
    (b'\\xe9\\x96\\xb2\\xe5\\xb6\\x86\\xe6\\x9f\\x8a\\xe9\\x80\\x89\\xe8\\x82\\xa1', b'Rerun'),
    
    # Fix any remaining "?" in JSX closing tags (from garbled replacement)
    (b'?/Text>', b'</Text>'),
    (b'?/Tag>', b'</Tag>'),
    (b'?/Space>', b'</Space>'),
    
    # Line 340: garbled DESCRIPTIONS label
    (b'<Descriptions.Item label="\\xe4\\xbb\\xb7\\xe9\\x94\\x8b\\xe7\\x89\\xb8">', b'<Descriptions.Item label="Price">'),
]

count = 0
for old, new in fixes:
    if old in data:
        data = data.replace(old, new)
        count += 1

# Also scan for remaining garbled in Descriptions labels
import re
# Find all Descriptions.Item label attributes
idx = 0
while True:
    idx = data.find(b'<Descriptions.Item label="', idx)
    if idx < 0:
        break
    end_quote = data.find(b'"', idx + 24)
    if end_quote > idx:
        label = data[idx+24:end_quote]
        if any(b > 127 for b in label):
            # Replace with generic label
            new_label = b'Field'
            data = data[:idx+24] + new_label + data[end_quote:]
            count += 1
            print(f'Fixed Descriptions label: {label[:20]}... -> {new_label}')
    idx = end_quote + 1

with open(fp, 'wb') as f:
    f.write(data)
print(f'Applied {count} fixes')
