"""Fix missing closing quotes on placeholders after dimension cleanup"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix: placeholder="min\r => placeholder="min"\r
data = data.replace(b'placeholder="min\r', b'placeholder="min"\r')
data = data.replace(b'placeholder="max\r', b'placeholder="max"\r')

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed placeholder quotes')
