'use strict';

const net = require('net');
const http = require('http');
const https = require('https');
const dns = require('dns');
const childProcess = require('child_process');
const { Worker } = require('worker_threads');

const CANARY_IP = '192.0.2.1';
const CANARY_HOST = 'vbss-net-guard-canary.invalid';
const results = [];

function add(name, ok, detail) {
  results.push({ name, ok: Boolean(ok), detail: String(detail || '') });
}

function isBlocked(err) {
  return Boolean(err && (err.code === 'VBSS_NET_GUARD_BLOCKED' || String(err.message).includes('[net-guard]')));
}

function withTimeout(promise, ms) {
  return Promise.race([promise, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms))]);
}

async function main() {
  add('guard carregado no processo', Boolean(globalThis.__vbssNetGuard), globalThis.__vbssNetGuard ? 'ok' : 'ausente');

  try {
    await withTimeout(fetch(`https://${CANARY_HOST}/`), 3000);
    add('fetch para host externo', false, 'a requisicao nao foi bloqueada');
  } catch (err) {
    add('fetch para host externo', isBlocked(err), err.message);
  }

  await new Promise((resolve) => {
    const sock = net.connect(443, CANARY_IP);
    const t = setTimeout(() => { add('net.connect para IP externo', false, 'sem bloqueio em 3s'); sock.destroy(); resolve(); }, 3000);
    sock.on('error', (err) => { clearTimeout(t); add('net.connect para IP externo', isBlocked(err), err.message); resolve(); });
    sock.on('connect', () => { clearTimeout(t); add('net.connect para IP externo', false, 'conectou'); sock.destroy(); resolve(); });
  });

  try {
    https.get(`https://${CANARY_HOST}/`);
    add('https.get para host externo', false, 'nao lancou erro');
  } catch (err) {
    add('https.get para host externo', isBlocked(err), err.message);
  }

  await new Promise((resolve) => {
    dns.lookup(CANARY_HOST, (err) => { add('dns.lookup de nome externo', isBlocked(err), err ? err.message : 'resolveu'); resolve(); });
  });

  try {
    await dns.promises.resolve4(CANARY_HOST);
    add('dns.promises.resolve4 de nome externo', false, 'resolveu');
  } catch (err) {
    add('dns.promises.resolve4 de nome externo', isBlocked(err), err.message);
  }

  await new Promise((resolve) => {
    const server = http.createServer((req, res) => res.end('ok'));
    server.listen(0, '127.0.0.1', async () => {
      const { port } = server.address();
      try {
        const res = await withTimeout(fetch(`http://127.0.0.1:${port}/`), 3000);
        add('loopback continua liberado (fetch 127.0.0.1)', (await res.text()) === 'ok', `porta ${port}`);
      } catch (err) {
        add('loopback continua liberado (fetch 127.0.0.1)', false, err.message);
      }
      server.close(resolve);
    });
  });

  await new Promise((resolve) => {
    const code = `fetch('https://${CANARY_HOST}/').then(()=>process.stdout.write('VAZOU'),e=>process.stdout.write(globalThis.__vbssNetGuard && String(e.message).includes('[net-guard]') ? 'BLOQUEADO' : 'SEM-GUARD:'+e.message))`;
    const child = childProcess.spawn(process.execPath, ['-e', code], { env: process.env, stdio: ['ignore', 'pipe', 'ignore'] });
    let out = '';
    child.stdout.on('data', (d) => { out += d; });
    child.on('close', () => { add('processo node filho herda o guard', out === 'BLOQUEADO', out); resolve(); });
  });

  await new Promise((resolve) => {
    const code = `const { parentPort } = require('worker_threads'); fetch('https://${CANARY_HOST}/').then(()=>parentPort.postMessage('VAZOU'),e=>parentPort.postMessage(String(e.message).includes('[net-guard]') ? 'BLOQUEADO' : 'SEM-GUARD:'+e.message));`;
    const w = new Worker(code, { eval: true });
    const t = setTimeout(() => { add('worker thread herda o guard', false, 'timeout'); w.terminate(); resolve(); }, 5000);
    w.on('message', (m) => { clearTimeout(t); add('worker thread herda o guard', m === 'BLOQUEADO', m); w.terminate(); resolve(); });
    w.on('error', (err) => { clearTimeout(t); add('worker thread herda o guard', false, err.message); resolve(); });
  });

  if (globalThis.__vbssNetGuard) {
    const hardened = globalThis.__vbssNetGuard.hardenChromeArgs(['--no-sandbox', '--disable-features=Translate', '--headless=new']);
    const ok = !hardened.includes('--no-sandbox')
      && hardened.some((a) => a.startsWith('--proxy-server=http://127.0.0.1:'))
      && hardened.some((a) => a.startsWith('--host-resolver-rules=MAP * ~NOTFOUND'))
      && hardened.some((a) => a.startsWith('--disable-features=Translate,'))
      && hardened.includes('--disable-background-networking');
    add('flags de isolamento do Chrome aplicadas', ok, hardened.join(' '));
  }

  process.stdout.write(JSON.stringify(results));
}

main().catch((err) => {
  results.push({ name: 'selftest', ok: false, detail: err.message });
  process.stdout.write(JSON.stringify(results));
});
