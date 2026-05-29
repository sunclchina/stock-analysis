"""Fix missing closing brace for ternary in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# The structure needs: ternary -> {cond ? <Empty/> : <Table ... />}
# Line 330 has: `{!hasRun ? <Empty ...`
# Line 334 ends with: `locale={{...}} />`
# We need a `}` after the `/>` to close the ternary

# Find the close of the Table element and add closing brace
lines = data.split(b'\n')
for i in range(len(lines)):
    line = lines[i]
    if b'locale={{ emptyText:' in line:
        # Add closing brace after />\r
        line = line.rstrip(b'\r')
        if line.rstrip().endswith(b'/>') or line.rstrip().endswith(b'/>\n'):
            lines[i] = line.rstrip() + b'}\r'
            print(f'Fixed line {i+1}: added closing }}')
        break

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print('Done')
