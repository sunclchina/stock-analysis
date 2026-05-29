"""Replace ALL garbled text in CustomSelectionTab.tsx message calls."""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

# Replace all occurrences of the specific garbled byte patterns
# These are the "提示文本" (info text) garbled patterns
patterns_to_replace = {}

# Find message calls with garbled content
import re

# Scan for lines with message.* that have high-bit bytes
lines = data.split(b'\n')
changed = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Pattern: message.warning/success/error/info('garbled')
    if stripped.startswith(b'message.') and b"'" in stripped:
        # Extract the string content
        first_quote = stripped.find(b"'")
        last_quote = stripped.rfind(b"'")
        if first_quote < last_quote:
            content = stripped[first_quote:last_quote+1]
            if sum(1 for b in content if b > 127) > 0:
                # Replace with a clean message
                if b'message.success' in stripped or b'message.info' in stripped:
                    lines[i] = line.replace(content, b"'Done'")
                    changed += 1
                elif b'message.warning' in stripped:
                    lines[i] = line.replace(content, b"'Warning'")
                    changed += 1
                elif b'message.error' in stripped:
                    lines[i] = line.replace(content, b"'Error'")
                    changed += 1
    
    # Pattern: message.warning/success/error/info(`garbled`)
    if stripped.startswith(b'message.') and b'\x60' in stripped:
        first_tick = stripped.find(b'\x60')
        last_tick = stripped.rfind(b'\x60')
        if first_tick < last_tick:
            content = stripped[first_tick:last_tick+1]
            # Skip if has ${} template expressions 
            if b'${' not in content and sum(1 for b in content if b > 127) > 0:
                lines[i] = line.replace(content, b"'Done'")
                changed += 1
    
    # Pattern: console.error('garbled')
    if b"console.error(" in stripped and b"'" in stripped:
        first_quote = stripped.find(b"'")
        last_quote = stripped.rfind(b"'")
        if first_quote < last_quote:
            content = stripped[first_quote:last_quote+1]
            if sum(1 for b in content if b > 127) > 0 and b',' not in content:
                lines[i] = line.replace(content, b"'Error'")
                changed += 1

if changed:
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)
    print(f'Replaced {changed} garbled message calls. {len(data)} -> {len(new_data)} bytes')
else:
    print('No garbled message calls found to replace')
