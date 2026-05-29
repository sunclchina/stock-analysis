"""Fix line 184 - add missing closing brace"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
data = data.replace(
    b'if (results.length === 0) { message.warning(\'Please check your input\')',
    b'if (results.length === 0) { message.warning(\'No data\'); return; }'
)
with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
