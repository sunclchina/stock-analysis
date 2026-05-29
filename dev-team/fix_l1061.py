"""Fix line 1061 - replace garbled description"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find the garbled description= line
idx = data.find(b'description="' + b'\xe5\xbd\x95')
if idx >= 0:
    print(f'Found description at {idx}')
    # Find the end of the description value
    end_marker = data.find(b'\r', idx)
    if end_marker >= 0:
        # Replace from idx to end with clean content
        new_content = b'description="Add more filter conditions or reduce existing criteria to narrow results"'
        data = data[:idx] + new_content + data[end_marker:]
        print('Replaced garbled description')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
