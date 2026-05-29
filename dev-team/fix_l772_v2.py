"""Fix trailing quote on line 772"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
data = data.replace(b"'Grade A' },'", b"'Grade A' },")
with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
