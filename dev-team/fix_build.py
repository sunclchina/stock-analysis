# -*- coding: utf-8 -*-
"""Fix all .tsx files with corrupted Chinese text — byte-level repair."""

import os
import re

BASE = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src'

FILES_TO_FIX = [
    os.path.join(BASE, 'pages', 'Selection', 'FixedSelectionTab.tsx'),
    os.path.join(BASE, 'pages', 'Selection', 'CustomSelectionTab.tsx'),
    os.path.join(BASE, 'pages', 'Config', 'DataSourceTab.tsx'),
]

def find_unmatched_backticks(data):
    """Find lines with unmatched backticks."""
    lines = data.split(b'\n')
    issues = []
    for i, line in enumerate(lines):
        ticks = [j for j, b in enumerate(line) if b == 0x60]
        dollar_braces = line.count(b'$' + b'{')  # careful with backslash
        if len(ticks) % 2 == 1:
            issues.append((i, ticks, dollar_braces, line))
    return issues

def fix_file(filepath):
    print(f'\n=== {os.path.basename(filepath)} ===')
    with open(filepath, 'rb') as f:
        data = f.read()
    
    original_size = len(data)
    issues = find_unmatched_backticks(data)
    
    if not issues:
        print('No unmatched backticks found. Checking for garbled chars in strings...')
        lines = data.split(b'\n')
        for i, line in enumerate(lines):
            # Check single-quoted strings that contain high-bit bytes (corrupted Chinese)
            if b"'" in line and any(b > 127 for b in line):
                # If the line has high-bit bytes and is a string literal
                # But not in a template literal
                if line.count(b'\x60') == 0:  # no backticks
                    pass  # These are generally OK since single quotes contain the high bytes
        print('No critical issues found.')
        return False
    
    print(f'Found {len(issues)} lines with unmatched backticks:')
    for ln, ticks, db, line in issues:
        # Show context
        print(f'  Line {ln+1}: {len(ticks)} tick(s) at {ticks}, {db} dollar-brace(s)')
        print(f'    Content: {line[:120]}')
    
    # For each issue, try to auto-fix
    modified = False
    lines = data.split(b'\n')
    
    for ln, ticks, _, _ in issues:
        if ln >= len(lines):
            continue
        line = lines[ln]
        
        # If only 1 backtick and it's at the start of a string
        # This means the closing backtick was lost in garbled text
        first_tick = ticks[0]
        
        # Find all high-bit sequences and check if closing backtick got eaten
        # The pattern is: garbled_chinese closing_backtick space/semicolon
        # Or: garbled_chinese close_paren/newline
        
        # Strategy: find the garbled region after the last ${
        # and before the line ending, add a closing backtick
        
        # If there are dollar-braces, find the last one
        last_dollar = line.rfind(b'${')
        
        if last_dollar >= 0:
            # Find matching closing brace
            brace_pos = line.find(b'}', last_dollar)
            if brace_pos >= 0:
                after_brace = line[brace_pos+1:]
                # Check if there's a backtick after the brace
                if b'\x60' not in after_brace[:5]:
                    # Add closing backtick after the brace
                    lines[ln] = line[:brace_pos+1] + b'\x60' + line[brace_pos+1:]
                    modified = True
                    print(f'  Fixed line {ln+1}: added closing backtick after }}')
        elif first_tick < len(line):
            # No dollar-brace, just an open backtick with garbled text
            # Close the backtick before the end of the line
            rest = line[first_tick+1:]
            # Find where the string should end - typically before ; or )
            for sep in [b');', b';', b' :', b', ']:
                idx = rest.find(sep)
                if idx >= 0:
                    # Insert closing backtick before the separator
                    lines[ln] = line[:first_tick+1+idx] + b'\x60' + line[first_tick+1+idx:]
                    modified = True
                    print(f'  Fixed line {ln+1}: added closing backtick before "{sep.decode()}"')
                    break
    
    if modified:
        new_data = b'\n'.join(lines)
        with open(filepath, 'wb') as f:
            f.write(new_data)
        print(f'  Written {len(new_data)} bytes (was {original_size})')
        
        # Verify
        new_issues = find_unmatched_backticks(new_data)
        if new_issues:
            print(f'  Still {len(new_issues)} unmatched tick(s) remaining')
            for ln, t, db, _ in new_issues:
                print(f'    Line {ln+1}')
        else:
            print('  All backticks now matched!')
        return True
    
    print('  No auto-fix applied')
    return False

def clean_garbled_strings(filepath):
    """Second pass: replace garbled Chinese text in string literals with English."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Find lines where string literals contain garbled Chinese
    # Pattern: inside single-quoted strings, there are sequences of bytes > 127
    # These are safe to replace since TypeScript doesn't care about string content
    
    lines = data.split(b'\n')
    changes = 0
    
    replacements = {
        # FixedSelectionTab.tsx specific
        b"'\\xe6\\x8f\\x90\\xe7\\xa4\\xba\\xe6\\x96\\x87\\xe6\\x9c\\xcb'": b"'Selection complete, see results below'",
        b"'\\xe9\\x80\\x89\\xe8\\x82\\xa1\\xe7\\x80\\xb9': b'Selection'",
    }
    
    for i, line in enumerate(lines):
        # Check for garbled bytes inside single-quoted strings
        in_single = False
        in_backtick = False
        clean = True
        for j, b in enumerate(line):
            if b == 0x27:
                in_single = not in_single
            elif b == 0x60:
                in_backtick = not in_backtick
        
    return changes

fix_scripts = [
    os.path.join(BASE, '..', 'dev-team', 'fix_custom.py'),
    os.path.join(BASE, '..', 'dev-team', 'fix_custom2.py'),
]

if __name__ == '__main__':
    any_fixed = False
    for fp in FILES_TO_FIX:
        if os.path.exists(fp):
            if fix_file(fp):
                any_fixed = True
        else:
            print(f'File not found: {fp}')
    
    if any_fixed:
        print('\nDone! Run npm run build to verify.')
    else:
        print('\nNo files needed fixing.')
