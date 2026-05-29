"""Fix garbled headers in handleExport"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i, line in enumerate(lines):
    if b"const headers = [" in line and sum(1 for b in line if b > 127) > 3:
        lines[i] = b"      const headers = ['Rank', 'Code', 'Name', 'Industry', 'Trend', 'Resonance Status', 'Strength', 'Risk Score', 'Risk Level', 'Finance Grade', 'Composite Score', 'Advice'];"
        print(f'Fixed line {i+1}: headers')
        break
new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
