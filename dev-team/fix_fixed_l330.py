"""Fix line 330 empty description"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Replace the garbled description with clean text
# Original: {!hasRun ? <Empty description="GARBLEDTEXT" image={Empty.PRESENTED_IMAGE_SIMPLE} />
old = b'{!hasRun ? <Empty description="'
idx = data.find(old)
if idx >= 0:
    rest = data[idx+len(old):]
    end_dq = rest.find(b'"')
    if end_dq >= 0 and end_dq < 200:
        new = b'{!hasRun ? <Empty description="Run selection to start" image={Empty.PRESENTED_IMAGE_SIMPLE} />'
        data = data[:idx] + new + data[idx+len(old)+end_dq+1:]
        print('Fixed line 330 empty description')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
