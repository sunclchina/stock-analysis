"""Fix garbled headers array in handleExport"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Fix line 185 - the headers array in handleExport
for i, line in enumerate(lines):
    if b"const headers = [" in line and sum(1 for b in line if b > 127) > 5:
        lines[i] = b"      const headers = ['Rank', 'Code', 'Name', 'Industry', 'Trend', 'Resonance', 'Strength', 'Risk Score', 'Risk Level', 'Fin Grade', 'Composite', 'Advice', 'Watchlisted'];"
        print(f'Fixed line {i+1}: headers array')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
