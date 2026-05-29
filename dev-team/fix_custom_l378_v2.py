"""Fix missing \r on line 378 and add semicolons"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Fix line 378: missing \r
data = data.replace(
    b"message.warning('Results limited to 500, add more conditions')\n      } else if",
    b"message.warning('Results limited to 500, add more conditions');\r\n      } else if"
)

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
