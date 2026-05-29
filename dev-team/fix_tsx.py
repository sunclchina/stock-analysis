# -*- coding: utf-8 -*-
"""Fix garbled Chinese text in TSX files by replacing specific byte sequences."""

import os

BASE = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src'

def fix_file_fixed_selection():
    """Fix FixedSelectionTab.tsx - replace garbled layerDescriptions."""
    fp = os.path.join(BASE, 'pages', 'Selection', 'FixedSelectionTab.tsx')
    with open(fp, 'rb') as f:
        data = f.read()
    
    original = data
    lines = data.split(b'\n')
    
    # Find layerDescriptions start
    for i, line in enumerate(lines):
        if b'const layerDescriptions = [' in line:
            # Replace lines i through i+5 (6 lines)
            new_lines = [
                b'  const layerDescriptions = [',
                b"    { name: 'L1', label: 'L1 Base Filter', desc: 'Remove ST/suspended/low-liq/low-price/new stocks' },",
                b"    { name: 'L2', label: 'L2 Tech Coarse', desc: '6 light indicators all met' },",
                b"    { name: 'L3', label: 'L3 Deep Refine', desc: '3 mandatory + >=2 optional + tech removal' },",
                b"    { name: 'L4', label: 'L4 Fin Event', desc: 'Fin safety + no event risk' },",
                b"    { name: 'L5', label: 'L5 Composite', desc: 'Score >=85 + capacity control' },",
                b'  ];',
            ]
            # Find the end of layerDescriptions
            end_i = i
            for j in range(i, min(i+10, len(lines))):
                if b'  ];' in lines[j] and j > i:
                    end_i = j
                    break
            
            print(f'Found layerDescriptions at lines {i+1} to {end_i+1}')
            print(f'Old line {i+1}: {lines[i][:120]}')
            print(f'Old line {end_i+1}: {lines[end_i][:120]}')
            
            # Replace
            lines = lines[:i] + new_lines + lines[end_i+1:]
            break
    
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)
    print(f'Fixed FixedSelectionTab.tsx: {len(original)} -> {len(new_data)} bytes')

def fix_file_custom_selection():
    """Fix CustomSelectionTab.tsx - fix unmatched backticks and garbled text."""
    fp = os.path.join(BASE, 'pages', 'Selection', 'CustomSelectionTab.tsx')
    with open(fp, 'rb') as f:
        data = f.read()
    
    lines = data.split(b'\n')
    changes = 0
    
    # Fix 1: line with warning message and unmatched backtick
    for i, line in enumerate(lines):
        ticks = [j for j, b in enumerate(line) if b == 0x60]
        if len(ticks) == 1 and b'${' in line:
            # Single backtick with dollar-brace - need to find and add closing backtick
            last_brace = line.rfind(b'}')
            if last_brace >= 0 and (last_brace + 1 >= len(line) or line[last_brace + 1:last_brace + 5].count(b'\x60') == 0):
                lines[i] = line[:last_brace+1] + b'\x60' + line[last_brace+1:]
                changes += 1
                print(f'CustomSelection: Fixed line {i+1}: added closing backtick')
        elif len(ticks) == 0 and b'${' in line and b'$' not in line[:5]:
            # Dollar-brace without any backticks - shouldn't happen
            print(f'CustomSelection: Line {i+1}: ${{ }} without backticks')
    
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)
    if changes:
        print(f'Fixed CustomSelectionTab.tsx: {len(data)} -> {len(new_data)} bytes, {changes} changes')

def fix_data_source_tab():
    """Fix DataSourceTab.tsx - fix unmatched backticks."""
    fp = os.path.join(BASE, 'pages', 'Config', 'DataSourceTab.tsx')
    with open(fp, 'rb') as f:
        data = f.read()
    
    lines = data.split(b'\n')
    
    for i, line in enumerate(lines):
        ticks = [j for j, b in enumerate(line) if b == 0x60]
        if len(ticks) % 2 == 1 and b'${' in line:
            last_brace = line.rfind(b'}')
            if last_brace >= 0:
                lines[i] = line[:last_brace+1] + b'\x60' + line[last_brace+1:]
                print(f'DataSourceTab: Fixed line {i+1}')
    
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)

def clean_garbled_messages(filepath):
    """Replace corrupted Chinese strings in message/text calls with English."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Replace garbled message text
    # Pattern: message.success/error/info/warning with garbled Chinese
    replacements = [
        (b"message.success(\xe9\x80\x89\xe8\x82\xa1\xe7\x80\xb9", b"message.success(\"Selection "),
        (b"message.error(\xef\xac\x81)", b'message.error("Action failed")'),
        (b"message.info(\xef\xac\x81)", b'message.info("Info")'),
    ]
    
    for old, new in replacements:
        if old in data:
            data = data.replace(old, new)
            print(f'  Replaced: {old[:30]}...')
    
    with open(filepath, 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    fix_file_fixed_selection()
    fix_file_custom_selection()
    fix_data_source_tab()
    
    # Clean up garbled messages in FixedSelectionTab
    fp = os.path.join(BASE, 'pages', 'Selection', 'FixedSelectionTab.tsx')
    print(f'\nCleaning messages in FixedSelectionTab.tsx...')
    clean_garbled_messages(fp)
    
    fp = os.path.join(BASE, 'pages', 'Selection', 'CustomSelectionTab.tsx')
    print(f'\nCleaning messages in CustomSelectionTab.tsx...')
    clean_garbled_messages(fp)
    
    print('\nDone. Run npm run build to verify.')
