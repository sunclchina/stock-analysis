"""Fix lines 288 and 333-334"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

# Line 288: Add missing { for JSX expression
for i, line in enumerate(lines):
    if b'L0:All A-shares totalStockCount' in line:
        old = line
        # Add opening '{' before 'totalStockCount'
        idx = line.find(b'totalStockCount')
        if idx > 0:
            lines[i] = line[:idx] + b'{' + line[idx:]
        print(f'Line {i+1}: fixed JSX expression opening')
        break

# Line 333-334: Close pagination object properly  
for i, line in enumerate(lines):
    if b'showTotal: (total, range) =>' in line and b'/ ${total} total' in line:
        # Check if line ends with closing braces
        if not line.rstrip().endswith(b'}'):
            lines[i] = lines[i].rstrip(b'\r') + b' }}\r'
        print(f'Line {i+1}: fixed pagination closing')
        break

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'{len(data)} -> {len(new_data)} bytes')
