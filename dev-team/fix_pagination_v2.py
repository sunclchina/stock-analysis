"""Fix pagination closing braces properly"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Replace the showTotal line - remove trailing } and ,
# Old: ` },\r\n                }\r\n
# New: `\r\n                }}\r\n
data = data.replace(
    b'` },\r\n                }\r\n                locale={{',
    b'`\r\n                }}\r\n                locale={{'
)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed pagination braces')
