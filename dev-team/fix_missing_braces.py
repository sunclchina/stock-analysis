# -*- coding: utf-8 -*-
"""Fix missing closing braces in CustomSelectionTab.tsx"""
import os

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')

for i, line in enumerate(lines):
    # Fix line 517: missing closing brace
    stripped = line.strip()
    if stripped.startswith(b'if (!templateName.trim())'):
        lines[i] = b'    if (!templateName.trim()) { message.warning(b"Enter name"); return; }'
        print(f'Fixed line {i+1}: if (!templateName.trim())')
    
    # Fix line 519: missing closing brace  
    if stripped.startswith(b'if (Object.keys(dims).length === 0)'):
        lines[i] = b'    if (Object.keys(dims).length === 0) { message.warning(b"No conditions"); return; }'
        print(f'Fixed line {i+1}: if (Object.keys(dims).length === 0)')

new_data = b'\n'.join(lines)
with open(fp, 'wb') as f:
    f.write(new_data)
print(f'{len(data)} -> {len(new_data)} bytes')
