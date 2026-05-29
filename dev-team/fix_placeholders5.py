"""Fix all remaining double-quote placeholder issues"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Replace all placeholder="GARBLED"" patterns
data = data.replace(b'placeholder="\xe6\x9c\xaf\xe7\x9b\x98\xe7\x81\x8f""', b'placeholder="min"')
data = data.replace(b'placeholder="\xe6\x9c\xaf\xe7\x9b\x98\xe6\xbe\xb6""', b'placeholder="max"')

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed double-quote placeholders')
