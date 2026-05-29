"""Fix garbled option labels in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith(b"{ value:") and b"label:" in s:
        if b"green" in s and b"\xe9\xa6\x83" in s:
            lines[i] = b'              { value: "green", label: "Green - Safe" },'
            print(f'Fixed line {i+1}: green label')
        elif b"yellow" in s and b"\xe9\xa6\x83" in s:
            lines[i] = b'              { value: "yellow", label: "Yellow - Watch" },'
            print(f'Fixed line {i+1}: yellow label')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
