"""Fix entire line 598 in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Line 598 (0-indexed 597)  
for i in range(595, 605):
    if i < len(lines):
        line = lines[i]
        # Check if it has garbled title string
        if b"'Resonance Status'resonanceStatus'" in line:
            lines[i] = b"    { title: 'Resonance Status', dataIndex: 'resonanceStatus', key: 'resonanceStatus', width: 90,"
            print(f'Fixed line {i+1}')
            break

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
