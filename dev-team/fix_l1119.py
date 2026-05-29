"""Fix lines 1112 button text and 1119 empty description"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 1112: button text
data = data.replace(b'>\xe9\x96\xb2\xe5\xb6\x86\xe6\x9f\x8a\xe9\x80\x89\xe8\x82\xa1<', b'>Rerun<')

# Fix line 1119: Empty description with garbled text
# Find <Empty description="GARBLED? 
idx = data.find(b'<Empty description="' + b'\xe7\x92\x87')
if idx >= 0:
    end_dq = data.find(b'"', idx + 20)
    if end_dq > idx and end_dq - idx < 300:
        # Replace the garbled content between the quotes
        data = data[:idx+20] + b'Configure dimensions and run selection' + data[end_dq:]
        print('Fixed Empty description')

with open(fp, 'wb') as f:
    f.write(data)
print('Done')
