"""Fix null byte on line 1009"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
# Remove null byte and the rest of the broken line
data = data.replace(b'unCheckedChildren=\x00', b'unCheckedChildren="Off"')
with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
