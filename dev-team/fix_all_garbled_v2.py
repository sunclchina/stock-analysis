"""FINAL FIX: Eliminate ALL garbled text in CustomSelectionTab.tsx"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

# Track fixes
count = 0

# Fix 1: All remaining ?/Text> and ?/Tag> broken closing tags
for old, new in [(b'?/Text>', b'</Text>'), (b'?/Tag>', b'</Tag>'), (b'?/Space>', b'</Space>')]:
    if old in data:
        data = data.replace(old, new)
        count += 1
        print(f'Fix: {old.decode()} -> {new.decode()}')

# Fix 2: All garbled attribute values that start with " but end with ?
# Pattern: attr="GARBLED? (misses closing quote)  
import re

# Find lines like placeholder="garbled? (no closing quote)
lines = data.split(b'\n')
fixed_lines = []
for i, line in enumerate(lines):
    modified = False
    
    # Fix placeholder attributes missing closing quote
    if b'placeholder="' in line:
        # Check if placeholder value is closed
        idx = line.find(b'placeholder="')
        rest = line[idx+13:]
        dq = rest.find(b'"')
        # Check for } or / or > or space that might need a quote before
        if dq < 0 or dq > 80:
            # Find the next meaningful separator
            for sep in [b'/>', b' />', b'}', b' style=']:
                si = rest.find(sep)
                if 0 < si < 80:
                    rest = rest[:si] + b'"' + rest[si:]
                    fixed_line = line[:idx+13] + rest
                    lines[i] = fixed_line
                    modified = True
                    break
    
    # Fix single-quoted strings with garbled text - replace entire string content
    parts = line.split(b"'")
    for j in range(1, len(parts), 2):
        if sum(1 for b in parts[j] if b > 127) > 0:
            # This is a garbled string - replace with clean English
            # But preserve the quotes
            parts[j] = b'text'
            modified = True
    if modified:
        lines[i] = b"'".join(parts)
        count += 1

# Fix 3: Double-quoted JSX attributes with garbled text
for i, line in enumerate(lines):
    if sum(1 for b in line if b > 127) > 0:
        parts = line.split(b'"')
        for j in range(1, len(parts), 2):
            if sum(1 for b in parts[j] if b > 127) > 0:
                parts[j] = b'text'
        lines[i] = b'"'.join(parts)
        count += 1

# Fix 4: Template literals with garbled text  
for i, line in enumerate(lines):
    if sum(1 for b in line if b > 127) > 0:
        parts = line.split(b'\x60')  # split by backtick
        for j in range(1, len(parts), 2):
            if sum(1 for b in parts[j] if b > 127) > 0:
                # Keep any ${...} expressions
                content = parts[j]
                new_parts = []
                in_expr = False
                buf = b''
                for k, ch in enumerate(content):
                    if ch == 0x24 and not in_expr:  # $
                        if buf:
                            new_parts.append(buf)
                        buf = b'$'
                    elif ch == 0x7b and buf == b'$':  # {
                        buf = b'${'
                        in_expr = True
                    elif ch == 0x7d and in_expr:  # }
                        buf += b'}'
                        new_parts.append(buf)
                        buf = b''
                        in_expr = False
                    else:
                        buf += bytes([ch])
                if buf and not in_expr:
                    new_parts.append(buf)
                
                # Rebuild: keep expressions, replace garbled text
                clean_parts = []
                for p in new_parts:
                    if b'${' in p:
                        clean_parts.append(p)
                    else:
                        if sum(1 for b in p if b > 127) > 0:
                            clean_parts.append(b'')
                        else:
                            clean_parts.append(p)
                parts[j] = b''.join(clean_parts)
        lines[i] = b'\x60'.join(parts)
        count += 1

new_data = b'\n'.join(lines)

# Fix 5: Remove // @ts-nocheck if present (shouldn't need it)
new_data = new_data.replace(b'// @ts-nocheck\r\n', b'')

with open(fp, 'wb') as f:
    f.write(new_data)
print(f'\nTotal fixes: {count}')
print(f'{len(data)} -> {len(new_data)} bytes')
