"""Fix garbled JSX text nodes in CustomSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Find lines with high-bit bytes that are raw JSX text (not inside any quotes)
for i, line in enumerate(lines):
    # Check if this is a text node between JSX tags
    stripped = line.strip()
    
    # Line 952: garbled text
    if b'\xe9\x97\x87\xe7\x9b\x98' in stripped and len(stripped) < 60:
        lines[i] = b'            Configure resonance settings'
        print(f'Fixed line {i+1}: raw text')
    
    # Line 954: garbled text with multiCount expression
    if b'\xe9\xa1\xb9\xe7\x99\xb8' in stripped and b'multiCount' in stripped:
        lines[i] = b'            Items selected (max: {multiCount})'
        print(f'Fixed line {i+1}: multiCount text')
    
    # Line 1026: garbled fallback text
    if b'\xe9\x90\x90\xe7\x91\xb0' in stripped:
        lines[i] = b'          Enable this section to configure conditions'
        print(f'Fixed line {i+1}: fallback text')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
