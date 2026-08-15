// Minimaler Werkzeugbau fuer diese Probe -- kein Produktivcode. Zwei
// Aufgaben in einem Skript, weil beide nur localhost sehen (Sandbox
// no-network.sb erlaubt ausschliesslich das): :8934 liefert index.html +
// bundle.js/.css aus, :8933 nimmt das Messergebnis per GET entgegen und
// schreibt es nach ergebnis.json, sobald es eintrifft.
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import { extname, join } from 'node:path';

const DIR = new URL('.', import.meta.url).pathname;
const OUT = join(DIR, 'ergebnis.json');

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

createServer(async (req, res) => {
  const path = req.url === '/' ? '/index.html' : req.url;
  try {
    const body = await readFile(join(DIR, path));
    res.writeHead(200, { 'content-type': MIME[extname(path)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end();
  }
}).listen(8934, '127.0.0.1');

createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1:8933');
  if (url.pathname === '/ergebnis') {
    const data = url.searchParams.get('data');
    await writeFile(OUT, data, 'utf-8');
  }
  res.writeHead(200);
  res.end();
}).listen(8933, '127.0.0.1');

console.error('serve_and_log: :8934 (seite), :8933 (log) bereit');
