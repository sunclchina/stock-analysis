"""Fix missing backtick in message line"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Replace using raw byte operations
data = data.replace(
    b'message.success(Selection complete: ',
    b'message.success(BACKTICKSelection complete: '
)
data = data.replace(
    b' stocks passed filtering);',
    b' stocks passed filteringBACKTICK);'
)
# Now replace BACKTICK with actual backtick (0x60)
data = data.replace(b'BACKTICK', b'\x60')

with open(fp, 'wb') as f:
    f.write(data)
print('Fixed')
