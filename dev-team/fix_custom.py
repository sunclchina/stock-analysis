import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx', 'rb') as f:
    data = f.read()

# Fix 1: Line 378 - missing closing backtick
old1 = b'        message.warning(`\xe7\xbc\x81\xe6\x92\xb4\xe7\x81\x89\xe7\x93\x92\xe5\x91\xb0\xe7\xb9\x83500\xe5\x8f\x96\xee\x81\x84\xe5\x87\xa1\xe6\x88\x90\xee\x81\x85\xe6\x9f\x87\xe5\xb1\xbd\xe7\xbc\x93\xe7\x92\x81\xee\x86\xbc\xee\x96\x83\xe9\x8d\x94\xe7\x8a\xb5\xe7\xad\x9b\xe9\x80\x89\xe5\xa4\x8b\xe6\xbd\xaf\xe4\xbb\xb7\xe7\xa6\xb6);\r\n'
new1 = b'        message.warning(`Results exceed 500, add more conditions to narrow scope`);\r\n'
count1 = data.count(old1)
print(f'Fix 1: Found {count1} occurrences')
if count1 > 0:
    data = data.replace(old1, new1)
else:
    # Try without \r
    old1_no_r = old1.replace(b'\r\n', b'\n')
    count1_no_r = data.count(old1_no_r)
    print(f'Fix 1 (no \\r): Found {count1_no_r}')
    if count1_no_r > 0:
        data = data.replace(old1_no_r, new1.replace(b'\r\n', b'\n'))

# Fix 2: Line 382 - garbled text  
old2 = b'        message.info(`\xe9\x80\x89\xe5\xa4\x8a\xe5\x9a\xad ${items.length} \xe5\x8f\x96\xee\x81\x8e\xe7\xb4\x9d\xe5\xaf\xa4\xe9\xb8\xbf\xee\x86\x85\xe6\xbe\xa7\xe7\x82\xb2\xe5\xa7\x9e\xe9\x8f\x87\xe6\x9d\x91\xee\x98\xbf\xe6\x9d\xa1\xe2\x80\xb2\xe4\xbb\xb6\xe7\xbc\x82\xe2\x95\x81\xe7\x9a\xac\xe8\x8c\x83\xe5\x9b\xb4`);\r\n'
new2 = b'        message.info(`Found ${items.length} results, consider adding more conditions`);\r\n'
count2 = data.count(old2)
print(f'Fix 2: Found {count2} occurrences')
if count2 > 0:
    data = data.replace(old2, new2)
else:
    old2_no_r = old2.replace(b'\r\n', b'\n')
    count2_no_r = data.count(old2_no_r)
    print(f'Fix 2 (no \\r): Found {count2_no_r}')
    if count2_no_r > 0:
        data = data.replace(old2_no_r, new2.replace(b'\r\n', b'\n'))

# Fix 3: Line 384 - missing closing backtick
old3 = b'        message.success(`\xe9\x80\x89\xe8\x82\xa1\xe7\x80\xb9\xe5\xb1\xbe\xe5\x9e\x9a\xe5\xb1\xbd\xe5\x8f\xa1 ${items.length} \xe5\x8f\x96\xee\x81\x87\xe7\xbb\x81\xe3\x84\xa9\xe7\x9b\x98\xe6\xb0\xb3\xe7\xb9\x83\xe7\xad\x9b\xe7\x9b\x98\xe5\xa1\xa6);\r\n'
new3 = b'        message.success(`Selection complete: ${items.length} stocks passed filters`);\r\n'
count3 = data.count(old3)
print(f'Fix 3: Found {count3} occurrences')
if count3 > 0:
    data = data.replace(old3, new3)
else:
    old3_no_r = old3.replace(b'\r\n', b'\n')
    count3_no_r = data.count(old3_no_r)
    print(f'Fix 3 (no \\r): Found {count3_no_r}')
    if count3_no_r > 0:
        data = data.replace(old3_no_r, new3.replace(b'\r\n', b'\n'))

# Fix 4: Line 1142 - pagination showTotal template (unclosed)
idx4_start = data.find(b'showTotal: (total, range) => `')
if idx4_start >= 0:
    # Find the end of this line
    end_line = data.find(b'\n', idx4_start)
    line4 = data[idx4_start:end_line+1]
    print(f'Fix 4: Found at offset {idx4_start}: {repr(line4)}')
    new4 = b'                  showTotal: (total, range) => `${range[0]}-${range[1]} / Total ${total}`,\n'
    data = data.replace(line4, new4)

# Fix 5: Line 1184 - template literal (unclosed)
idx5_start = data.find(b'{tmpl.max_results ? `\xe4\xb8\x80\xe5\xa9\x87\xe6\xaa\xba')
if idx5_start >= 0:
    end_line = data.find(b'\n', idx5_start)
    line5 = data[idx5_start:end_line+1]
    print(f'Fix 5: Found at offset {idx5_start}: {repr(line5)}')
    new5 = b'                          {tmpl.max_results ? `Max ${tmpl.max_results} results` : ''}\n'
    data = data.replace(line5, new5)

# Also fix other garbled text that might cause issues: message.info('提示文本')
data = data.replace(b"message.info('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')\r\n", b"message.info('No results found')\r\n")
data = data.replace(b"message.info('\xe6\x8f\x90\xe7\xa4\xba\xe6\x96\x87\xe6\x9c\xac')\n", b"message.info('No results found')\n")

# Fix console.error garbled text
data = data.replace(b"console.error('\xe8\x87\xaa\xe5\xae\x9a\xe4\xb9\x89\xe5\xa4\x90\xe7\x9b\x98\xe8\x82\xa1\xe6\xbe\xb6\xe8\xbe\xab\xe8\xa7\xa6:', err);\r\n", b"console.error('Custom selection failed:', err);\r\n")
data = data.replace(b"console.error('\xe8\x87\xaa\xe5\xae\x9a\xe4\xb9\x89\xe5\xa4\x90\xe7\x9b\x98\xe8\x82\xa1\xe6\xbe\xb6\xe8\xbe\xab\xe8\xa7\xa6:', err);\n", b"console.error('Custom selection failed:', err);\n")

with open(r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx', 'wb') as f:
    f.write(data)
print('Write complete')
