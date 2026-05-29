"""
快速基准测试 — 逐一测试各API端点的响应时间
"""
import socket
import time
import sys

def test(path, label=''):
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(8)
    try:
        s.connect(('127.0.0.1', 8000))
        req = 'GET %s HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' % path
        s.send(req.encode())
        s.shutdown(socket.SHUT_WR)
        data = b''
        while True:
            try:
                chunk = s.recv(65536)
                if not chunk: break
                data += chunk
            except:
                break
        s.close()
        e = time.time() - t0
        parts = data.decode(errors='replace').split('\r\n\r\n', 1)
        body = parts[1] if len(parts) > 1 else ''
        status = parts[0].split(' ')[1] if b'HTTP' in data else '?'
        print('%5.2fs %s %6dB  %s' % (e, status, len(body), label or path[:50]))
    except Exception as ex:
        print('%5.2fs FAIL        %s' % (time.time() - t0, label or path[:50]))

print('=' * 60)
print('Benchmark - testing %d endpoints' % len(sys.argv[1:]) if len(sys.argv) > 1 else 'default')
print('=' * 60)

endpoints = sys.argv[1:] if len(sys.argv) > 1 else [
    '/api/v1/health',
    '/api/v1/market/quote/000001',
    '/api/v1/market/quotes/000001',
    '/api/v1/market/overview',
    '/api/v1/market/is-trading-day',
    '/api/v1/config/datasource',
]

for p in endpoints:
    test(p)
