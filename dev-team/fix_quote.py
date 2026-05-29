"""Fix stray quote"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
data = data.replace(b'"Advice"];\'\\r', b'"Advice"];\\r')  
data = data.replace(b'"Advice"];\'', b'"Advice"];')
with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
