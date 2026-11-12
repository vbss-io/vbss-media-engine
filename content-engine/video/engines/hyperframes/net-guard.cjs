'use strict';

if (!globalThis.__vbssNetGuard) {
  const fs = require('fs');
  const path = require('path');
  const net = require('net');
  const tls = require('tls');
  const http = require('http');
  const https = require('https');
  const dns = require('dns');
  const dgram = require('dgram');
  const childProcess = require('child_process');
  const Module = require('module');

  const LOG_PATH = process.env.VBSS_NET_GUARD_LOG
    || path.resolve(__dirname, '..', '..', '.sandbox', 'net-guard.log');
  const BLOCK_CODE = 'VBSS_NET_GUARD_BLOCKED';

  const LOOPBACK_NAMES = new Set(['localhost', 'localhost.', 'ip6-localhost', 'ip6-loopback']);

  function stripBrackets(host) {
    return host.startsWith('[') && host.endsWith(']') ? host.slice(1, -1) : host;
  }

  function isLoopbackHost(rawHost) {
    if (rawHost === undefined || rawHost === null || rawHost === '') return true;
    const host = stripBrackets(String(rawHost).trim().toLowerCase());
    if (LOOPBACK_NAMES.has(host) || host.endsWith('.localhost')) return true;
    if (net.isIPv4(host)) return host.startsWith('127.');
    if (net.isIPv6(host)) {
      if (host === '::1' || host === '0:0:0:0:0:0:0:1') return true;
      const mapped = host.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/);
      return Boolean(mapped && mapped[1].startsWith('127.'));
    }
    return false;
  }

  function record(kind, target) {
    const entry = {
      when: new Date().toISOString(),
      pid: process.pid,
      kind,
      target: String(target),
      where: (new Error().stack || '').split('\n').slice(3, 6).map((l) => l.trim()).join(' | '),
    };
    try {
      fs.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
      fs.appendFileSync(LOG_PATH, JSON.stringify(entry) + '\n');
    } catch (_) {
    }
    try {
      process.stderr.write(`[net-guard] BLOQUEADO ${kind} -> ${target}\n`);
    } catch (_) {
    }
  }

  function blockedError(kind, target) {
    const err = new Error(`[net-guard] conexao de saida bloqueada (${kind} -> ${target}). O motor de video roda 100% local.`);
    err.code = BLOCK_CODE;
    return err;
  }

  function hostFromUrlLike(input) {
    try {
      if (input && typeof input === 'object' && 'url' in input && typeof input.url === 'string') {
        return new URL(input.url).hostname;
      }
      return new URL(String(input)).hostname;
    } catch (_) {
      return null;
    }
  }

  function isLocalUrl(input) {
    const raw = input && typeof input === 'object' && 'url' in input ? input.url : String(input);
    if (/^(data|blob|file):/i.test(raw)) return true;
    const host = hostFromUrlLike(input);
    return host !== null && isLoopbackHost(host);
  }

  const originalSocketConnect = net.Socket.prototype.connect;
  net.Socket.prototype.connect = function guardedConnect(...args) {
    let options = args[0];
    if (Array.isArray(options)) options = options[0];
    let host;
    let port;
    let ipcPath;
    if (options !== null && typeof options === 'object') {
      ipcPath = options.path;
      host = options.host;
      port = options.port;
    } else if (typeof options === 'string' && !/^\d+$/.test(options)) {
      ipcPath = options;
    } else {
      port = options;
      host = typeof args[1] === 'string' ? args[1] : undefined;
    }
    if (ipcPath === undefined && !isLoopbackHost(host)) {
      const target = `${host}:${port}`;
      record('net.connect', target);
      const err = blockedError('net.connect', target);
      process.nextTick(() => this.destroy(err));
      return this;
    }
    return originalSocketConnect.apply(this, args);
  };

  function wrapRequest(mod, name, protocol) {
    const original = mod[name];
    mod[name] = function guardedRequest(...args) {
      let host;
      const first = args[0];
      if (typeof first === 'string' || first instanceof URL) {
        host = hostFromUrlLike(first);
      } else if (first && typeof first === 'object') {
        host = first.hostname || first.host;
        if (host && typeof host === 'string' && !first.hostname) host = host.replace(/:\d+$/, '');
      }
      if (host && !isLoopbackHost(host)) {
        const target = `${protocol}//${host}`;
        record(`${protocol.replace(':', '')}.${name}`, target);
        throw blockedError(`${protocol.replace(':', '')}.${name}`, target);
      }
      return original.apply(this, args);
    };
  }
  wrapRequest(http, 'request', 'http:');
  wrapRequest(http, 'get', 'http:');
  wrapRequest(https, 'request', 'https:');
  wrapRequest(https, 'get', 'https:');

  if (typeof globalThis.fetch === 'function') {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = function guardedFetch(input, init) {
      if (!isLocalUrl(input)) {
        const target = typeof input === 'object' && input && 'url' in input ? input.url : String(input);
        record('fetch', target);
        return Promise.reject(blockedError('fetch', target));
      }
      return originalFetch.call(this, input, init);
    };
  }

  if (typeof globalThis.WebSocket === 'function') {
    const OriginalWebSocket = globalThis.WebSocket;
    globalThis.WebSocket = new Proxy(OriginalWebSocket, {
      construct(target, args) {
        if (!isLocalUrl(args[0])) {
          record('WebSocket', args[0]);
          throw blockedError('WebSocket', args[0]);
        }
        return Reflect.construct(target, args);
      },
    });
  }

  function guardLookupFn(owner, name, label) {
    const original = owner[name];
    if (typeof original !== 'function') return;
    owner[name] = function guardedLookup(hostname, ...rest) {
      if (!isLoopbackHost(hostname)) {
        record(label, hostname);
        const err = blockedError(label, hostname);
        const cb = rest.reverse().find((a) => typeof a === 'function');
        if (cb) {
          process.nextTick(() => cb(err));
          return undefined;
        }
        return Promise.reject(err);
      }
      return original.call(this, hostname, ...rest);
    };
  }

  const DNS_FNS = ['lookup', 'lookupService', 'resolve', 'resolve4', 'resolve6', 'resolveAny', 'resolveCname',
    'resolveCaa', 'resolveMx', 'resolveNaptr', 'resolveNs', 'resolvePtr', 'resolveSoa', 'resolveSrv', 'resolveTxt',
    'reverse'];
  for (const fn of DNS_FNS) {
    guardLookupFn(dns, fn, `dns.${fn}`);
    if (dns.promises) guardLookupFn(dns.promises, fn, `dns.promises.${fn}`);
    if (dns.Resolver) guardLookupFn(dns.Resolver.prototype, fn, `dns.Resolver.${fn}`);
    if (dns.promises && dns.promises.Resolver) guardLookupFn(dns.promises.Resolver.prototype, fn, `dns.promises.Resolver.${fn}`);
  }

  for (const fn of ['send', 'connect']) {
    const original = dgram.Socket.prototype[fn];
    dgram.Socket.prototype[fn] = function guardedDgram(...args) {
      const address = args.find((a, i) => i > 0 && typeof a === 'string');
      if (address !== undefined && !isLoopbackHost(address)) {
        record(`dgram.${fn}`, address);
        throw blockedError(`dgram.${fn}`, address);
      }
      return original.apply(this, args);
    };
  }

  function normalizeExe(p) {
    return path.resolve(String(p)).toLowerCase();
  }

  function isBrowserExecutable(file) {
    if (typeof file !== 'string') return false;
    const configured = process.env.HYPERFRAMES_BROWSER_PATH || process.env.PRODUCER_HEADLESS_SHELL_PATH;
    if (configured && normalizeExe(file) === normalizeExe(configured)) return true;
    return /(^|[\\/])(chrome|chromium|msedge|chrome-headless-shell)(\.exe)?$/i.test(file);
  }

  function loadIsolation() {
    try {
      const data = JSON.parse(process.env.VBSS_CHROME_ISOLAMENTO || '');
      if (Array.isArray(data.flags) && data.flags.length && Array.isArray(data.recursos_desligados)) return data;
    } catch (_) {
    }
    return null;
  }

  const ISOLATION = loadIsolation();

  function hardenChromeArgs(args) {
    if (!ISOLATION) {
      record('chrome.spawn', 'VBSS_CHROME_ISOLAMENTO ausente');
      throw blockedError('chrome.spawn', 'flags de isolamento ausentes (VBSS_CHROME_ISOLAMENTO); rode pelo render.py');
    }
    const out = [];
    let disableFeaturesSeen = false;
    for (const arg of args) {
      if (arg === '--no-sandbox' || arg === '--disable-setuid-sandbox' || arg === '--no-zygote') continue;
      if (/^--(proxy-server|proxy-pac-url|proxy-auto-detect|host-resolver-rules|remote-debugging-address)=/.test(arg)) continue;
      if (arg.startsWith('--disable-features=')) {
        disableFeaturesSeen = true;
        const merged = new Set(arg.slice('--disable-features='.length).split(',').filter(Boolean));
        for (const f of ISOLATION.recursos_desligados) merged.add(f);
        out.push(`--disable-features=${[...merged].join(',')}`);
        continue;
      }
      out.push(arg);
    }
    if (!disableFeaturesSeen) out.push(`--disable-features=${ISOLATION.recursos_desligados.join(',')}`);
    out.push(...ISOLATION.flags);
    return out;
  }

  function versionProbeShim(args) {
    if (!Array.isArray(args) || args.length !== 1 || args[0] !== '--version') return null;
    const version = process.env.VBSS_BROWSER_VERSION || '';
    const script = version
      ? `process.stdout.write(${JSON.stringify(`Google Chrome ${version}\n`)})`
      : 'process.exit(1)';
    return [process.execPath, ['-e', script]];
  }

  for (const fn of ['spawn', 'execFile', 'execFileSync', 'spawnSync']) {
    const original = childProcess[fn];
    childProcess[fn] = function guardedSpawn(file, args, ...rest) {
      if (isBrowserExecutable(file)) {
        const shim = versionProbeShim(args);
        if (shim) return original.call(this, shim[0], shim[1], ...rest);
        if (Array.isArray(args)) args = hardenChromeArgs(args);
      }
      return original.call(this, file, args, ...rest);
    };
  }

  globalThis.__vbssNetGuard = Object.freeze({
    logPath: LOG_PATH,
    isLoopbackHost,
    hardenChromeArgs,
    blockCode: BLOCK_CODE,
  });

  if (typeof Module.syncBuiltinESMExports === 'function') Module.syncBuiltinESMExports();
}
