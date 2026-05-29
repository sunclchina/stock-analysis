"""Fix garbled JSX text nodes in CustomSelectionTab.tsx by line number"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    lines = f.read().split(b'\n')

# Fix specific lines
targets = {
    951: b'            Configure resonance settings',
    953: b'            Items selected (max: {multiCount})',
    1025: b'          Enable this section to configure conditions',
}

for line_num, new_content in targets.items():
    idx = line_num - 1  # 0-indexed
    if idx < len(lines):
        old = lines[idx]
        lines[idx] = new_content + b'\r'
        print(f'Fixed line {line_num}: {old[:40]} -> {new_content[:40]}')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
