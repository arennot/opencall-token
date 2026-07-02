const http = require('http');
const fs = require('fs');
const path = require('path');

const root = 'C:\\Users\\arenn\\Documents\\Codex\\2026-06-30\\opencall-token\\outputs\\opencall-token';
const mime = { html: 'text/html; charset=utf-8', js: 'application/javascript; charset=utf-8', css: 'text/css' };

http.createServer((req, res) => {
  let f = req.url === '/' ? 'index.html' : req.url.slice(1);
  f = path.join(root, f);
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    const ext = path.extname(f).slice(1);
    res.writeHead(200, { 'Content-Type': mime[ext] || 'text/plain' });
    res.end(data);
  });
}).listen(8000, () => console.log('Server running on http://localhost:8000'));