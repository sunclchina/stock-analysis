"""Fix garbled DimensionPanel titles and remaining issues"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 1076: fundamental panel title
data = data.replace(b'title="\xe5\x9f\xba\xe6\x9c\xac\xe9\x9d\x9e\xe3\x88\xa2\xe7\xad\x9b\xe9\x80\x89?', b'title="Fundamental"')

# Fix line 1079: technical panel title
data = data.replace(b'title="\xe6\x8a\x80\xe7\x9b\x98\xe6\x9c\xaf\xe9\x9d\xa2\xe7\xad\x9b\xe7\x9b\x98?', b'title="Technical"')

# Fix line 1082: resonance panel title (missing closing quote)
data = data.replace(b'title="\xe5\x85\xb1\xe6\x8c\xaf\xe7\xb1\xbb\xe7\xad\x9b\xe9\x80\x89', b'title="Resonance"')

# Fix line 1088: garbled text inside <Text>
data = data.replace(b'\xe7\xbc\x81\xe6\x9d\x91\xe5\xae\xb3\xe9\x97\x82\xe6\x92\xae\xe7\x9b\x98\xe6\x98\x8f\xe7\xb7\xab\xe4\xb8\x80?AND\xe5\xa0\x9f\xe5\xa2\x8d\xe6\x9c\xaf\xe5\xa4\x8a\xe5\x90\xaf\xe9\x90\xa2\xe3\x84\xa7\xe7\xbb\xb4\xe5\xba\xa6\xef\xb9\x80\xe6\x82\x93\xe9\x8f\x83\xe8\x88\xb5\xe5\xbc\xa7\xe7\x93\x92\xe7\xad\xb9\xe7\xb4\x9a', b'AND logic applies between dimensions. Enable each dimension to configure conditions.')

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed dimension panel titles')
