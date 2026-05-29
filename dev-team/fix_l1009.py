"""Fix line 1009 - broken switch labels"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
data = data.replace(
    b'checkedChildren="\xe7\x9b\x98" unCheckedChildren="\xe9\x8d\x8f?',
    b'checkedChildren="On" unCheckedChildren=\x00'  # placeholder
)
# Actually use a simpler approach
data = data.replace(b'unCheckedChildren="\xe9\x8d\x8f?', b'unCheckedChildren="Off"')
data = data.replace(b'checkedChildren="\xe7\x9b\x98"', b'checkedChildren="On"')
with open(fp, 'wb') as f:
    f.write(data)
print('Fixed line 1009')
