"""Fix headers array in CustomSelectionTab.tsx handleExport."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

for i, line in enumerate(lines):
    # Fix headers array with garbled Chinese
    if b"const headers = [" in line and sum(1 for b in line if b > 127) > 10:
        lines[i] = b"      const headers = ['Rank', 'Code', 'Name', 'Industry', 'Trend', 'Resonance', 'Strength', 'Risk Score', 'Risk Level', 'Fin Grade', 'Composite Score', 'Advice'];"
        print(f'Fixed line {i+1}: headers array')
    
    # Fix garbled message.success("Export successful")  
    if b"message.success(" in line and b'\xe6\x88\x90\xe5\x8a\x9f' in line and sum(1 for b in line if b > 127) > 5:
        if b'\x60' in line:
            lines[i] = line[:line.find(b'\x60')] + b'"Export successful"' + line[line.rfind(b'\x60')+1:]
        else:
            lines[i] = b"      message.success('Export successful');"
        print(f'Fixed line {i+1}: export success message')
    
    # Fix garbled in column definitions
    for garbled, clean in [
        (b'\xe9\x96\xb9\xe6\x8e\x92\xe6\xae\xbf', b'Rank'),
        (b'\xe4\xbb\xb7\xe4\xb6\x9d\xe7\x92\xb2', b'Code'),
        (b'\xe5\x90\x8e\xe7\xbd\xae\xe2\x84\x83', b'Name'),
    ]:
        if garbled in line:
            lines[i] = line.replace(garbled, clean)

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Written: {len(data)} -> {len(new_data)} bytes')
