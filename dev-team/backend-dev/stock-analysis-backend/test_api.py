"""快速测试后端API"""
import socket, time, json, sys

host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
path = sys.argv[3] if len(sys.argv) > 3 else '/api/v1/health'

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
s.connect((host, port))
s.send(f'GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'.encode())
time.sleep(0.3)
data = b''
try:
    while True:
        chunk = s.recv(65536)
        if not chunk: break
        data += chunk
except: pass
s.close()

resp = data.decode(errors='replace')
if not resp:
    print('NO RESPONSE')
    sys.exit(1)

status = resp.split('\r\n')[0].split(' ')[1] if '\r\n' in resp else 'unknown'
_, _, body = resp.partition('\r\n\r\n')
print(f'Status: {status}')
if body:
    d = json.loads(body)
    if isinstance(d, dict):
        for k in list(d.keys())[:3]:
            v = d[k]
            print(f'  {k}: {len(v) if isinstance(v, (list, dict, str)) else v}')
    print(json.dumps(d, ensure_ascii=False, indent=2)[:500])
