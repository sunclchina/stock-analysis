"""Fix line 1119 completely"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')
lines[1118] = b'              <Empty description="Configure dimensions and run selection" image={Empty.PRESENTED_IMAGE_SIMPLE} />'
with open(fp, 'wb') as f:
    f.write(b'\n'.join(lines))
print('Fixed line 1119')
