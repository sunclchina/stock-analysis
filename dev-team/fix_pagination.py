"""Fix pagination closing braces"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# The pagination structure: pagination={{ ... showTotal: ...` }, }}
# Should be: pagination={{ ... showTotal: ...` }}
# Remove the extra } from showTotal line
data = data.replace(
    b'` },\n                }\n                locale',
    b'`\n                }}\n                locale'
)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed pagination braces')
