"""Fix garbled Descriptions labels in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Check lines around 340-370
lines = data.split(b'\n')
for i in range(338, 370):
    if i < len(lines):
        line = lines[i]
        # Fix any garbled label="..."
        if b'<Descriptions.Item label=' in line:
            # Find label value
            qt = line.find(b'label=')
            dq = line.find(b'"', qt+6)
            if dq > qt:
                label_bytes = line[qt+7:dq]
                if any(b > 127 for b in label_bytes):
                    # Replace with clean label
                    lines[i] = line[:qt+7] + b'Field' + line[dq:]
                    print(f'Fixed line {i+1}: Descriptions label')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
