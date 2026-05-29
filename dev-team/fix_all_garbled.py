"""Comprehensive fix: replace ALL garbled Chinese text in FixedSelectionTab.tsx and CustomSelectionTab.tsx."""
import os

files = [
    r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx',
    r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx',
]

for fp in files:
    print(f'\n=== {os.path.basename(fp)} ===')
    with open(fp, 'rb') as f:
        data = f.read()
    
    lines = data.split(b'\n')
    changed = 0
    
    for i, line in enumerate(lines):
        # Find all string literals (single-quoted and backtick) with high-bit bytes
        # Strategy: find the complete string literal (between quotes/backticks)
        # and replace its content with clean English text
        
        # Check single-quoted strings with garbled text
        sq_parts = line.split(b"'")
        modified = False
        for j, part in enumerate(sq_parts):
            if j % 2 == 1:  # inside single quotes
                if sum(1 for b in part if b > 127) > 3:
                    # This is a garbled string - replace with clean text
                    # Preserve if it's a variable name or code pattern
                    sq_parts[j] = b'text'
                    modified = True
        
        if modified:
            line = b"'".join(sq_parts)
        
        # Check backtick strings with garbled text
        bt_parts = line.split(b'\x60')
        modified = False
        for j, part in enumerate(bt_parts):
            if j % 2 == 1:  # inside backticks
                if sum(1 for b in part if b > 127) > 3:
                    # Check if it contains ${} template expressions
                    if b'${' in part:
                        # Keep the ${} parts, replace garbled text around them
                        # Split by ${...}
                        template_parts = []
                        in_template = False
                        current = b''
                        for ch in part:
                            if ch == 0x24 and not in_template:
                                if current:
                                    template_parts.append(current)
                                current = b'$'
                            elif ch == 0x7b and current == b'$':
                                current = b'${'
                                in_template = True
                            elif ch == 0x7d and in_template:
                                current += b'}'
                                template_parts.append(current)
                                current = b''
                                in_template = False
                            elif in_template:
                                current += bytes([ch])
                            else:
                                current += bytes([ch])
                        if current:
                            template_parts.append(current)
                        
                        # Now template_parts alternates between text and ${...} templates
                        clean_parts = []
                        for k, tp in enumerate(template_parts):
                            if b'${' in tp:
                                clean_parts.append(tp)
                            else:
                                # Replace garbled text
                                if sum(1 for b in tp if b > 127) > 0:
                                    tp_clean = b''
                                clean_parts.append(tp)
                        bt_parts[j] = b''.join(clean_parts)
                    else:
                        # Pure text, no templates - just empty it
                        bt_parts[j] = b''
                    modified = True
        
        if modified:
            lines[i] = b'\x60'.join(bt_parts)
            changed += 1
        
        # Fix specific known garbled patterns
        if b"message.success(" in line and b'\xe5\xb7\xb2\xe5\x8a\xa0\xe8\xbd\xbd' in line:
            lines[i] = b"      message.success('Template loaded: ${tmpl.name}');" if b'${' in line else b"      message.success('Template loaded');"
            changed += 1
        
        if b"// \xe7" in line:  # garbled comment
            lines[i] = b"// (comment corrupted, replaced)"
            changed += 1
    
    new_data = b'\n'.join(lines)
    with open(fp, 'wb') as f:
        f.write(new_data)
    print(f'Changed {changed} lines. {len(data)} -> {len(new_data)} bytes')
