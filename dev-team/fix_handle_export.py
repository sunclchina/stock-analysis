"""Fix missing closing braces and garbled text"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 424: add missing closure for if block
data = data.replace(b"if (results.length === 0) { message.warning(\x27\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac\x27)", 
                     b"if (results.length === 0) { message.warning(\x27No data\x27); return; }")

# Fix line 432: garbled download filename 
data = data.replace(b'\xe8\x87\xaa\xe5\xae\x9a\xe4\xb9\x89\xe5\xa4\x90\xe7\x9b\x98\xe8\x82\xa1\xe7\xbc\x81\xe6\x92\xb4\xe7\x81\x89_', b'selection_results_')

# Fix line 435: garbled success message
data = data.replace(b"\x27\xe7\x80\xb5\xe7\x85\x8e\xe5\x9a\xad\xe6\x88\x90\xe6\x84\xac\xe5\xa7\x9b\x27", b"\x27Export OK\x27")

# Fix line 441: missing closure for if block
data = data.replace(b"if (!d) { message.warning(\x27\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac\x27)", 
                     b"if (!d) { message.warning(\x27Invalid\x27); return; }")

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
