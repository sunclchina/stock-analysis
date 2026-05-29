"""Replace problematic try/catch block with simpler version"""
fp = r'C:\Users\suncl\.openclaw\workspace\dev-team\frontend-dev\stock-analysis-frontend\src\pages\Selection\CustomSelectionTab.tsx'
with open(fp, 'rb') as f:
    data = f.read()

# Find the try block from line 350 to 393
try_start = b'    try {\r\n      const res = await customSelection(dims, maxResults);'
try_end = b'    }\r\n  }, [buildDimensions, maxResults, watchlistCodes]);'

# Locate the try block
start_idx = data.find(try_start)
end_idx = data.find(try_end, start_idx) if start_idx >= 0 else -1

if start_idx >= 0 and end_idx >= 0:
    # Replace the entire try/catch/finally with a simplified version
    replacement = b'''    try {
      const res = await customSelection(dims, maxResults);
      const rawItems = res?.items || [];
      const items = rawItems.map((item) => ({
        rank: item.rank,
        code: item.code,
        name: item.name,
        industry: item.industry || '',
        trendColor: item.trend_color,
        resonanceStatus: item.resonance_status,
        trendStrength: item.trend_strength || 0,
        riskScore: item.risk_score || 50,
        riskLevel: item.risk_level || 'medium',
        financeGrade: item.finance_grade || 'B',
        compositeScore: item.total_score || 0,
        operationAdvice: item.trade_advice || '',
        addedToWatchlist: watchlistCodes.has(item.code),
      }));
      setResults(items);
      setHasRun(true);
      if (res.truncated) {
        setTruncated(true);
        message.warning('Results limited to 500, add more conditions');
      } else if (items.length === 0) {
        message.info('No stocks found');
      }
    } catch (err) {
      console.error('Selection error:', err);
      message.error('Selection failed');
      setResults([]);
      setHasRun(true);
    } finally {
      setLoading(false);
    }'''
    
    # Calculate end of try block
    end_of_block = start_idx + len(try_start)
    # Find the closing })
    close_idx = data.find(b'  }, [', end_of_block)
    if close_idx < 0:
        close_idx = end_idx + len(try_end) - 4
    
    # Replace from try_start to the close before '  }, ['
    actual_start = start_idx
    actual_end = end_idx + len(try_end)
    
    data = data[:actual_start] + replacement + data[actual_end:]
    
    with open(fp, 'wb') as f:
        f.write(data)
    print(f'Replaced try/catch block')
else:
    print('Could not locate try block')
    if start_idx >= 0:
        print(f'try start found at {start_idx}')
    if end_idx >= 0:
        print(f'try end found at {end_idx}')
