"""Fix ALL remaining garbled text. Replace line 512 and check for other syntax issues."""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

# Direct byte-level fixes for known broken patterns
fixes = [
    # Line 512: message.success with garbled text
    (b'message.success(`\\xe5\\xae\\xb8\\xe6\\x8f\\x92\\xe5\\xa7\\x9e\\xe6\\x9d\\x9e\\xe8\\x8a\\xa5\\xc4\\x81\\xe6\\x9d\\xa1? ${tmpl.name}`)',
     b"message.success(`Template loaded: ${tmpl.name}`)"),
    
    # Line 517: message.warning with garbled text (no closing brace)
    (b"if (!templateName.trim()) { message.warning('\\xe6\\x8f\\x90\\xe7\\xa4\\xba\\xe6\\x96\\x87\\xe6\\x9c\\xac')",
     b"if (!templateName.trim()) { message.warning('Please enter template name')"),
    
    # Line 519: same garbled message.warning
    (b"if (Object.keys(dims).length === 0) { message.warning('\\xe6\\x8f\\x90\\xe7\\xa4\\xba\\xe6\\x96\\x87\\xe6\\x9c\\xac')",
     b"if (Object.keys(dims).length === 0) { message.warning('No conditions configured')"),
    
    # Line 330ish: getSuggestions failing error
    (b"console.error('\\xe8\\x87\\xaa\\xe5\\xae\\x9a\\xe4\\xb9\\x89\\xe9\\xbb\\xb7\\xe7\\x9b\\x98\\xe8\\x82\\xa1\\xe6\\xbe\\xb6\\xe8\\xbe\\xab\\xe8\\xa7\\xa6:', err)",
     b"console.error('Custom selection error:', err)"),
]

count = 0
for old_bytes, new_bytes in fixes:
    if old_bytes in data:
        data = data.replace(old_bytes, new_bytes)
        count += 1
        print(f'Fixed pattern: {old_bytes[:40]}')
    else:
        # Try matching just the relevant part
        print(f'Pattern not found, checking for near-match: {old_bytes[:30]}...')
        # Check if any bytes of the pattern exist
        part = old_bytes[:20]
        if part in data:
            # Find the context
            idx = data.find(part)
            print(f'  Found near {idx}: {data[idx:idx+80]}')

with open(fp, 'wb') as f:
    f.write(data)

print(f'\nApplied {count} fixes')
