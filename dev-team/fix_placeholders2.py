"""Fix ALL unclosed placeholder strings in CustomSelectionTab.tsx"""
import sys

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

count = 0
idx = 0
while True:
    qmark = chr(0x22)
    idx = data.find(b'placeholder=' + qmark.encode(), idx)
    if idx < 0:
        break
    
    rest = data[idx+13:]
    dq = rest.find(qmark.encode())
    
    if dq < 0 or dq > 60:
        for sep in [b' />', b'/>', b' style=', b'}', b'\r', b'\n']:
            si = rest.find(sep)
            if si >= 0 and si < 60:
                data = data[:idx+13+si] + qmark.encode() + data[idx+13+si:]
                count += 1
                idx = idx + 13 + si + 2
                break
        else:
            idx = idx + 14
    else:
        idx = idx + 13 + dq + 1

with open(fp, 'wb') as f:
    f.write(data)
print(f'Fixed {count} unclosed placeholder strings')
