"""Find braces inside single-quoted strings in FixedSelectionTab.tsx"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\FixedSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

lines = data.split(b'\n')
braces_in_strings = 0

for i, line in enumerate(lines):
    # Parse line for braces inside single-quoted strings
    in_single = False
    for j, b in enumerate(line):
        if b == 0x27:  # single quote
            in_single = not in_single
        elif b == 0x7b and in_single:  # { inside single-quoted string
            braces_in_strings += 1
        elif b == 0x7d and in_single:  # } inside single-quoted string
            braces_in_strings -= 1

print(f'Net brace imbalance from strings: {braces_in_strings}')
print(f'If this is 0, string braces match what Python counts.')

# Also check braces inside comments
in_comment = False
braces_in_comments = 0
for i, line in enumerate(lines):
    for j, b in enumerate(line):
        if b == ord('/') and j+1 < len(line) and line[j+1] == ord('/'):
            break  # rest of line is comment
        if b == ord('/') and j+1 < len(line) and line[j+1] == ord('*'):
            in_comment = True
        if b == ord('*') and j+1 < len(line) and line[j+1] == ord('/') and in_comment:
            in_comment = False
        if in_comment and (b == 0x7b or b == 0x7d):
            braces_in_comments += 1 if b == 0x7b else -1

print(f'Net brace imbalance from comments: {braces_in_comments}')
print(f'Total adjustment: {braces_in_strings + braces_in_comments}')
