"""Fix misplaced quotes in InputNumber placeholders"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix pattern: placeholder="...? ... { ... }"
# The ? at the end of placeholder value should be "
# But my fix added " at the line end instead

# Fix 1: Remove the misplaced " before } on subsequent lines
data = data.replace(b'?.min"}', b'?.min}')
data = data.replace(b'?.max"}', b'?.max}')

# Fix 2: Actually replace ? with " in the placeholder
# The pattern is: placeholder="GARBLED? (where ? should be closing ")
# Find all placeholder="...? patterns where ? is at the end
import re
lines = data.split(b'\n')
fixed = 0
for i, line in enumerate(lines):
    if b'placeholder=' in line:
        p = line.find(b'placeholder=')
        rest = line[p+13:]  # after placeholder="
        dq = rest.find(b'\x22')  # find "
        if dq >= 0 and dq < 80:
            content = rest[:dq]
            if content and content[-1:] == b'\x3f':  # ends with ?
                # Replace ? with "
                lines[i] = line[:p+13+dq-1] + b'\x22' + line[p+13+dq:]
                fixed += 1

if fixed:
    data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(data)
    print(f'Fixed {fixed} placeholder strings: replaced ? with "')
else:
    print('No fixes needed')
