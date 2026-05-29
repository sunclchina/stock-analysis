"""Fix all missing \r and semicolons in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Add missing \r and ; to lines
fixes = [
    (b"message.warning('Results limited to 500, add more conditions')\n      return;",
     b"message.warning('Results limited to 500, add more conditions');\r\n      return;"),
]

for old, new in fixes:
    if old in data:
        data = data.replace(old, new)
        print('Fixed missing CRLF/semicolons')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
