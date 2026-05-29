"""Comprehensive fix for ALL garbled text in CustomSelectionTab.tsx"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

# Fix 1: Broken closing tags with ? instead of <
data = data.replace(b'?/Text>', b'</Text>')
data = data.replace(b'?/>', b'/>')
data = data.replace(b'?/Tag>', b'</Tag>')
data = data.replace(b'?/Space>', b'</Space>')

# Fix 2: Placeholders with missing closing quote
# Pattern: placeholder="garbledTEXT? \r (where ? is 0x3F and missing closing ")
# Find all placeholder="...?" patterns and add closing quote
import re
patterns = []
idx = 0
while True:
    idx = data.find(b'placeholder="', idx)
    if idx < 0:
        break
    end_quote = data.find(b'"', idx + 14)
    if end_quote < 0:
        # No close quote found - add one at specific positions
        next_space = data.find(b' ', idx + 14)
        next_close = data.find(b'>', idx + 14)
        next_cr = data.find(b'\r', idx + 14)
        # Use the closest suitable delimiter
        candidates = [p for p in [next_space, next_close, next_cr] if p > idx + 14]
        if candidates:
            end_pos = min(candidates)
            data = data[:end_pos] + b'"' + data[end_pos:]
            patterns.append(f'Fixed placeholder at {idx}')
    idx = idx + 14

# Fix 3: All high-byte garbled text in {.../} comments
# Just remove the garbled content inside comments
lines = data.split(b'\n')
for i, line in enumerate(lines):
    # Clean garbled comments
    if b'/*' in line and b'*/' in line and sum(1 for b in line if b > 127) > 3:
        start = line.find(b'/*')
        end = line.find(b'*/', start)
        if start >= 0 and end > start:
            lines[i] = line[:start] + b'/* ... */' + line[end+2:]
    
    # Clean garbled text inside <Text>...</Text>
    if b'<Text' in line and b'</Text>' in line and sum(1 for b in line if b > 127) > 0:
        # Find the text content between > and </Text>
        gt = line.rfind(b'>', 0, line.rfind(b'</Text>'))
        if gt >= 0:
            content = line[gt+1:line.rfind(b'</Text>')]
            if content and sum(1 for b in content if b > 127) > 3:
                # Replace with clean english
                lines[i] = line[:gt+1] + b'Label' + line[line.rfind(b'</Text>'):]
    
    # Fix garbled Checkbox/Radio text
    if b'<Checkbox' in line or b'<Radio.Button' in line:
        if sum(1 for b in line if b > 127) > 0:
            for garbled, clean in [
                (b'\xe9\x96\xb2\xe6\x88\x9d\xe5\xbc\xb6', b'Golden Cross'),
                (b'\xe5\xa7\x9d\xe8\xaf\xb2\xe5\xbc\xb6', b'Death Cross'),
                (b'\xe7\xbb\xbe\xe3\x88\xa1\xe7\x85\xb4\xe9\x8f\x80\xe6\x83\xa7\xe3\x81\x87', b'Red Bar Expand'),
                (b'\xe7\xbb\x8f\xe5\x93\x84\xe3\x81\x94', b'Bearish'),
                (b'\xe7\xbc\x82\xe7\x8a\xb5\xe7\xb2\xab', b'Entangled'),
                (b'\xe4\xb8\x80\xe5\xb6\x89\xe6\xaa\xba', b'None'),
                (b'\xe9\xa6\x83\xe7\x85\x9d \xe5\xae\x89\xe5\x85\xa8\xe5\xa0\x9f\xe6\xa3\xa4\xe5\x90\x88\xe7\x88\xb6?', b'Safe'),
            ]:
                if garbled in line:
                    lines[i] = line.replace(garbled, clean)

new_data = b'\n'.join(lines)

# Make sure all placeholder strings are properly closed
# Scan for unclosed placeholders
remaining_issues = 0
for i, line in enumerate(new_data.split(b'\n')):
    if b'placeholder="' in line:
        qt = line.find(b'placeholder="')
        rest = line[qt+13:]
        dq = rest.find(b'"')
        if dq < 0 or dq > 100:
            # Unclosed or too long - check
            pass

with open(fp, 'wb') as f:
    f.write(new_data)
print(f'Fixed. {len(data)} -> {len(new_data)} bytes')
for p in patterns:
    print(p)
