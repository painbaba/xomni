#!/usr/bin/env python3
"""Live QR server: renders the WhatsApp pairing QR from qr_payload_live.txt
on every request; the browser page auto-refreshes every 3s so the code on
screen is always the latest payload written. Update the payload file on each
bridge rotation - no server restart needed. This is the RELIABLE path when
static PNG renders keep going stale (the ~20s Baileys rotation) and the user
ends up scanning expired codes ("can't link").

Usage:
  python3 qr_server.py                 # serves http://127.0.0.1:8765
  powershell Start-Process 'http://127.0.0.1:8765'   # open the tab
Verify: curl / -> 200 html, /qr.png -> 200 png (use Windows-style paths,
native Windows python3 cannot read MSYS /c/... paths)."""
import http.server
import socketserver
import io

PAYLOAD_FILE = r'C:\Users\HP\AppData\Local\hermes\whatsapp\qr_payload_live.txt'
PORT = 8765

HTML = '''<html><head><meta charset="utf-8"><title>WhatsApp QR - LIVE</title>
<style>
body{background:#0b141a;color:#fff;font-family:Segoe UI,Arial,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0}
img{width:min(72vh,72vw);border-radius:12px;box-shadow:0 0 40px rgba(37,211,102,.25)}
#st{font-size:15px;color:#8696a0;margin-top:18px}
#age{font-size:12px;color:#54656f;margin-top:6px}
</style></head>
<body>
<img id="q" src="/qr.png?t=0" alt="WhatsApp QR - if blank, wait 3s">
<div id="st">Scan with WhatsApp &rarr; Linked devices &rarr; Link a device</div>
<div id="age"></div>
<script>
let last='';
async function tick(){
  const t=Date.now();
  try{
    const r=await fetch('/qr.png?t='+t,{cache:'no-store'});
    if(!r.ok) throw 0;
    const b=await r.blob();
    if(b.size!==last){last=b.size;document.getElementById('q').src=URL.createObjectURL(b);}
    document.getElementById('age').textContent='live - refreshed '+new Date().toLocaleTimeString();
  }catch(e){document.getElementById('age').textContent='waiting for QR...';}
}
setInterval(tick,3000);tick();
</script></body></html>'''


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/qr.png'):
            try:
                raw = open(PAYLOAD_FILE, encoding='utf-8').read().strip()
                import qrcode
                img = qrcode.make(raw).resize((640, 640))
                buf = io.BytesIO()
                img.save(buf, 'PNG')
                data = buf.getvalue()
            except Exception:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            body = HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', PORT), H) as httpd:
    print(f'QR server on http://127.0.0.1:{PORT}')
    httpd.serve_forever()
