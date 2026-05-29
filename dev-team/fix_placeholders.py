"""Fix ALL unclosed placeholder quotes in CustomSelectionTab.tsx"""
import sys

fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'

with open(fp, 'rb') as f:
    data = f.read()

count = 0
idx = 0
while True:
    idx = data.find(b'placeholder="', idx)
    if idx < 0:
        break
    
    # Find the next quote after the placeholder opening
    next_quote = data.find(b'"', idx + 14)
    
    # Check if the close quote is within ~60 bytes (reasonable placeholder length)
    # Also check style={...} which shouldn't be matched
    if next_quote < 0 or next_quote > idx + 80:
        # Check if the end of line comes before any reasonable close quote
        eol = data.find(b'\r', idx + 14)
        if eol < 0 or eol > idx + 80:
            # Check if there's an end-of-attribute pattern like / or space
            for separator in [b'/>', b' />', b'\r']:
                sep_idx = data.find(separator, idx + 14)
                if 0 <= sep_idx <= idx + 60:
                    # Insert quote before separator
                    data = data[:sep_idx] + b'"' + data[sep_idx:]
                    count += 1
                    idx = sep_idx + 2
                    break
            else:
                idx = idx + 14
        else:
            # Check if the content before \r has a " hiding in garbled text
            content = data[idx+14:eol]
            # Remove trailing \r
            content = content.rstrip(b'\r').rstrip()
            # Insert quote at end of content
            data = data[:idx+14] + content + b'"' + data[eol:]
            count += 1
            idx = eol + 1
    else:
        idx = next_quote + 1

with open(fp, 'wb') as f:
    f.write(data)
print(f'Fixed {count} unclosed placeholder quotes')
