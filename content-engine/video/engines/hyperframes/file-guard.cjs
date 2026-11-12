'use strict';

if (!globalThis.__vbssFileGuard) {
  const fs = require('fs');
  const path = require('path');
  const childProcess = require('child_process');
  const Module = require('module');
  const { fileURLToPath } = require('url');
  const { isMainThread } = require('worker_threads');

  const WIN = process.platform === 'win32';
  const ENV_RAIZES = 'VBSS_FILE_GUARD_RAIZES';
  const LOG_PATH = process.env.VBSS_FILE_GUARD_LOG
    || path.resolve(__dirname, '..', '..', '.sandbox', 'file-guard.log');
  const BLOCK_CODE = 'VBSS_FILE_GUARD_BLOCKED';
  const CODIGO_ABORTO = 97;
  const LISTA_MAX_BYTES = 2 * 1024 * 1024;
  const EXT_LISTA = new Set(['.txt', '.ffconcat', '.concat']);
  const OPCAO_COM_ARQUIVO = /^-(?:filter_complex_script|filter_script|\/.+)$/;

  const orig = {
    realpathSync: fs.realpathSync.native || fs.realpathSync,
    existsSync: fs.existsSync,
    statSync: fs.statSync,
    readFileSync: fs.readFileSync,
    appendFileSync: fs.appendFileSync,
    mkdirSync: fs.mkdirSync,
  };

  let registrando = false;
  let abortando = false;

  function semPrefixoDeDispositivo(p) {
    if (/^\\\\\?\\UNC\\/i.test(p)) return `\\\\${p.slice(8)}`;
    if (/^\\\\[?.]\\[a-z]:/i.test(p)) return p.slice(4);
    return p;
  }

  function ehDispositivoInofensivo(p) {
    if (/^\\\\[?.]\\pipe\\/i.test(p)) return true;
    if (/^(?:\\\\[?.]\\)?(?:nul|con)$/i.test(p)) return true;
    return p === '-' || /^pipe:\d*$/i.test(p);
  }

  function caminhoReal(p) {
    const abs = path.resolve(semPrefixoDeDispositivo(p));
    const resto = [];
    let atual = abs;
    for (;;) {
      try {
        const real = orig.realpathSync(atual);
        return resto.length ? path.join(real, ...resto.reverse()) : real;
      } catch (_) {
      }
      const pai = path.dirname(atual);
      if (pai === atual) return abs;
      resto.push(path.basename(atual));
      atual = pai;
    }
  }

  function dentro(alvo, raiz) {
    const rel = path.relative(raiz, alvo);
    return rel === '' || (rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel));
  }

  function carregarRaizes() {
    const fixas = [__dirname, path.dirname(process.execPath)];
    let declaradas = null;
    try {
      const dados = JSON.parse(process.env[ENV_RAIZES] || '');
      if (Array.isArray(dados) && dados.length && dados.every((r) => typeof r === 'string' && r)) declaradas = dados;
    } catch (_) {
    }
    return {
      ausentes: declaradas === null,
      lista: [...fixas, ...(declaradas || [])].map(caminhoReal),
    };
  }

  const RAIZES = carregarRaizes();
  const PASTA_DO_SISTEMA = caminhoReal(path.join(process.env.SystemRoot || process.env.SYSTEMROOT || 'C:\\Windows', 'System32'));

  function permitido(alvo) {
    return RAIZES.lista.some((r) => dentro(alvo, r));
  }

  function registrar(tipo, alvo, detalhe) {
    const entrada = {
      when: new Date().toISOString(),
      pid: process.pid,
      kind: tipo,
      target: String(alvo),
      detail: detalhe ? String(detalhe).slice(0, 400) : undefined,
      where: (new Error().stack || '').split('\n').slice(3, 7).map((l) => l.trim()).join(' | '),
    };
    registrando = true;
    try {
      orig.mkdirSync(path.dirname(LOG_PATH), { recursive: true });
      orig.appendFileSync(LOG_PATH, `${JSON.stringify(entrada)}\n`);
    } catch (_) {
    } finally {
      registrando = false;
    }
    try {
      process.stderr.write(`[file-guard] BLOQUEADO ${tipo} -> ${alvo}: arquivo fora da pasta da composicao e das pastas do motor. Render abortado.\n`);
    } catch (_) {
    }
  }

  function abortar() {
    process.exitCode = CODIGO_ABORTO;
    if (abortando || !isMainThread) return;
    abortando = true;
    setTimeout(() => process.exit(CODIGO_ABORTO), 0);
  }

  function erroDeBloqueio(tipo, alvo) {
    const motivo = RAIZES.ausentes ? ` (${ENV_RAIZES} ausente: rode pelo render.py)` : '';
    const err = new Error(`[file-guard] acesso a arquivo fora da pasta da composicao bloqueado (${tipo} -> ${alvo})${motivo}. Copie o arquivo para assets/ da composicao.`);
    err.code = BLOCK_CODE;
    return err;
  }

  function bloquear(tipo, alvo, detalhe) {
    registrar(tipo, alvo, detalhe);
    abortar();
    return erroDeBloqueio(tipo, alvo);
  }

  function comoTexto(p) {
    if (typeof p === 'string') return p;
    if (Buffer.isBuffer(p)) return p.toString('utf8');
    if (p instanceof URL) return p.protocol === 'file:' ? fileURLToPath(p) : null;
    return null;
  }

  function alvoForaDasRaizes(bruto, base, exigirExistente) {
    if (registrando) return null;
    const texto = comoTexto(bruto);
    if (texto === null || texto === '') return null;
    if (texto.includes('\0')) return texto;
    if (ehDispositivoInofensivo(texto)) return null;
    const alvo = caminhoReal(base ? path.resolve(base, semPrefixoDeDispositivo(texto)) : texto);
    if (permitido(alvo)) return null;
    if (exigirExistente && !orig.existsSync(alvo)) return null;
    return alvo;
  }

  function soLeitura(flags) {
    if (flags === undefined || flags === null) return true;
    if (typeof flags === 'number') {
      const c = fs.constants;
      return (flags & (c.O_WRONLY | c.O_RDWR | c.O_CREAT | c.O_TRUNC | c.O_APPEND)) === 0;
    }
    return ['r', 'rs', 'sr'].includes(String(flags));
  }

  function flagsDeOpcoes(opcoes) {
    return opcoes && typeof opcoes === 'object' ? opcoes.flag : undefined;
  }

  function ultimoCallback(args) {
    for (let i = args.length - 1; i >= 0; i -= 1) if (typeof args[i] === 'function') return args[i];
    return null;
  }

  function guardarFs(dono, nome, rotulo, extrairAlvos, modo) {
    const original = dono && dono[nome];
    if (typeof original !== 'function') return;
    dono[nome] = function guardado(...args) {
      for (const [bruto, exigirExistente] of extrairAlvos(args)) {
        const alvo = alvoForaDasRaizes(bruto, null, exigirExistente);
        if (alvo === null) continue;
        const err = bloquear(rotulo, alvo);
        if (modo === 'promessa') return Promise.reject(err);
        if (modo === 'callback') {
          const cb = ultimoCallback(args);
          if (cb) {
            process.nextTick(() => cb(err));
            return undefined;
          }
        }
        throw err;
      }
      return original.apply(this, args);
    };
  }

  const leitura = (args) => [[args[0], soLeitura(flagsDeOpcoes(args[1]))]];
  const abertura = (args) => [[args[0], soLeitura(typeof args[1] === 'function' ? undefined : args[1])]];
  const copia = (args) => [[args[0], true], [args[1], false]];
  const fluxo = (args) => [[args[0], soLeitura(flagsDeOpcoes(args[1]))]];

  guardarFs(fs, 'readFile', 'fs.readFile', leitura, 'callback');
  guardarFs(fs, 'readFileSync', 'fs.readFileSync', leitura, 'sync');
  guardarFs(fs, 'open', 'fs.open', abertura, 'callback');
  guardarFs(fs, 'openSync', 'fs.openSync', abertura, 'sync');
  guardarFs(fs, 'createReadStream', 'fs.createReadStream', fluxo, 'sync');
  guardarFs(fs, 'copyFile', 'fs.copyFile', copia, 'callback');
  guardarFs(fs, 'copyFileSync', 'fs.copyFileSync', copia, 'sync');
  guardarFs(fs, 'cp', 'fs.cp', copia, 'callback');
  guardarFs(fs, 'cpSync', 'fs.cpSync', copia, 'sync');
  guardarFs(fs, 'openAsBlob', 'fs.openAsBlob', (args) => [[args[0], true]], 'promessa');
  guardarFs(fs, 'link', 'fs.link', copia, 'callback');
  guardarFs(fs, 'linkSync', 'fs.linkSync', copia, 'sync');
  guardarFs(fs, 'rename', 'fs.rename', copia, 'callback');
  guardarFs(fs, 'renameSync', 'fs.renameSync', copia, 'sync');
  const promessas = [fs.promises];
  try {
    const fsp = require('fs/promises');
    if (fsp !== fs.promises) promessas.push(fsp);
  } catch (_) {
  }
  for (const p of promessas) {
    guardarFs(p, 'readFile', 'fs.promises.readFile', leitura, 'promessa');
    guardarFs(p, 'open', 'fs.promises.open', abertura, 'promessa');
    guardarFs(p, 'copyFile', 'fs.promises.copyFile', copia, 'promessa');
    guardarFs(p, 'cp', 'fs.promises.cp', copia, 'promessa');
    guardarFs(p, 'link', 'fs.promises.link', copia, 'promessa');
    guardarFs(p, 'rename', 'fs.promises.rename', copia, 'promessa');
  }

  function semAspas(s) {
    const t = s.trim();
    return t.length >= 2 && /^["'].*["']$/.test(t) && t[0] === t[t.length - 1] ? t.slice(1, -1) : t;
  }

  function urlParaCaminho(u) {
    try {
      return fileURLToPath(u);
    } catch (_) {
      return u.replace(/^file:\/*/i, '') || u;
    }
  }

  function pareceCaminhoInteiro(s) {
    if (/^[a-z]:[\\/]/i.test(s) || /^\\\\/.test(s) || /^file:/i.test(s)) return true;
    if (/^\/[^/\s]+\/./.test(s)) return true;
    return /(^|[\\/])\.\.([\\/]|$)/.test(s);
  }

  function candidatosNoTexto(texto) {
    const achados = [];
    let resto = texto;
    for (const m of texto.matchAll(/"([^"\r\n]*)"|'([^'\r\n]*)'/g)) {
      const dentroDasAspas = m[1] !== undefined ? m[1] : m[2];
      if (pareceCaminhoInteiro(dentroDasAspas)) achados.push(dentroDasAspas);
    }
    resto = resto.replace(/"[^"\r\n]*"|'[^'\r\n]*'/g, ' ');
    for (const fonte of [texto, resto]) {
      for (const m of fonte.matchAll(/(?<![a-z0-9])file:[^\s'"|;,<>*?]*/gi)) achados.push(urlParaCaminho(m[0]));
    }
    for (const m of resto.matchAll(/(?<![a-z0-9])[a-z]\\*:[\\/][^\s'"|;,*?<>:]*/gi)) achados.push(m[0].replace(/^([a-z])\\*:/i, '$1:'));
    for (const m of resto.matchAll(/(?<![\w\\])\\\\[^\\/\s'"|;,*?<>:]+[\\/][^\s'"|;,*?<>:]*/g)) achados.push(m[0]);
    for (const m of resto.matchAll(/(?:^|[\s=;,|[\]])((?:[^\s'"=;,|*?<>[\]]*[\\/])?\.\.(?:[\\/][^\s'"=;,|*?<>[\]]*)?)(?=$|[\s=;,|[\]])/g)) achados.push(m[1]);
    return achados;
  }

  function candidatosDoArgumento(arg, cwd) {
    const achados = [];
    const inteiro = semAspas(arg);
    const partes = [inteiro];
    const igual = inteiro.indexOf('=');
    if (inteiro.startsWith('-') && igual > 0) partes.push(semAspas(inteiro.slice(igual + 1)));
    for (const p of partes) {
      if (pareceCaminhoInteiro(p)) {
        achados.push(/^file:/i.test(p) ? urlParaCaminho(p) : p);
      } else if (p.length < 260 && !/[\r\n*?<>|"]/.test(p) && p !== '.' && orig.existsSync(path.resolve(cwd, p))) {
        achados.push(p);
      }
    }
    return achados.concat(candidatosNoTexto(inteiro));
  }

  function lerListaOuScript(arquivo) {
    try {
      const st = orig.statSync(arquivo);
      if (!st.isFile() || st.size > LISTA_MAX_BYTES) return null;
      registrando = true;
      try {
        return orig.readFileSync(arquivo, 'utf8');
      } finally {
        registrando = false;
      }
    } catch (_) {
      return null;
    }
  }

  function entradasDeConcat(texto) {
    const achados = [];
    for (const linha of texto.split(/\r?\n/)) {
      const m = linha.match(/^\s*file\s+(.+?)\s*$/);
      if (!m) continue;
      let v = m[1];
      if (v.startsWith("'") && v.endsWith("'")) v = v.slice(1, -1).replace(/'\\''/g, "'");
      achados.push(v);
    }
    return achados;
  }

  function verificarProcesso(rotulo, arquivo, args, opcoes) {
    if (registrando) return;
    const cwd = opcoes && typeof opcoes === 'object' && opcoes.cwd ? String(opcoes.cwd) : process.cwd();
    const lista = Array.isArray(args) ? args.map((a) => String(a)) : [];
    const executavel = typeof arquivo === 'string' ? arquivo : '';
    const shell = Boolean(opcoes && typeof opcoes === 'object' && opcoes.shell);
    const problemas = [];

    const conferir = (candidato, base) => {
      const alvo = alvoForaDasRaizes(candidato, base, false);
      if (alvo !== null) problemas.push(alvo);
      return alvo === null;
    };

    if (executavel) {
      if (shell || /\s/.test(executavel.trim()) && !orig.existsSync(executavel)) {
        for (const cand of candidatosNoTexto(executavel)) conferir(cand, cwd);
      } else if (pareceCaminhoInteiro(executavel) || path.isAbsolute(executavel)) {
        const real = caminhoReal(path.resolve(cwd, executavel));
        if (!permitido(real) && !dentro(real, PASTA_DO_SISTEMA)) problemas.push(real);
      }
    }

    lista.forEach((arg, i) => {
      for (const cand of candidatosDoArgumento(arg, cwd)) {
        if (!conferir(cand, cwd)) continue;
        const real = caminhoReal(path.resolve(cwd, semPrefixoDeDispositivo(cand)));
        const anterior = i > 0 ? lista[i - 1] : '';
        const ehScript = OPCAO_COM_ARQUIVO.test(anterior);
        if (!ehScript && !EXT_LISTA.has(path.extname(real).toLowerCase())) continue;
        const conteudo = lerListaOuScript(real);
        if (conteudo === null) continue;
        for (const entrada of entradasDeConcat(conteudo)) conferir(entrada, path.dirname(real));
        for (const embutido of candidatosNoTexto(conteudo.replace(/\\:/g, ':'))) conferir(embutido, path.dirname(real));
      }
    });

    if (problemas.length) {
      const detalhe = [executavel, ...lista].join(' ').slice(0, 400);
      throw bloquear(rotulo, problemas[0], detalhe);
    }
  }

  function separarArgs(args, rest) {
    if (Array.isArray(args)) return [args, rest[0]];
    if (args && typeof args === 'object') return [[], args];
    return [[], rest[0]];
  }

  for (const fn of ['spawn', 'spawnSync', 'execFile', 'execFileSync']) {
    const original = childProcess[fn];
    if (typeof original !== 'function') continue;
    childProcess[fn] = function guardado(arquivo, args, ...rest) {
      const [lista, opcoes] = separarArgs(args, rest);
      verificarProcesso(`child_process.${fn}`, arquivo, lista, opcoes);
      return original.call(this, arquivo, args, ...rest);
    };
  }

  for (const fn of ['exec', 'execSync']) {
    const original = childProcess[fn];
    if (typeof original !== 'function') continue;
    childProcess[fn] = function guardado(comando, ...rest) {
      const opcoes = rest[0] && typeof rest[0] === 'object' ? rest[0] : undefined;
      verificarProcesso(`child_process.${fn}`, String(comando), [], { ...(opcoes || {}), shell: true });
      return original.call(this, comando, ...rest);
    };
  }

  {
    const original = childProcess.fork;
    if (typeof original === 'function') {
      childProcess.fork = function guardado(modulo, args, ...rest) {
        const [lista, opcoes] = separarArgs(args, rest);
        verificarProcesso('child_process.fork', process.execPath, [String(modulo), ...lista], opcoes);
        return original.call(this, modulo, args, ...rest);
      };
    }
  }

  globalThis.__vbssFileGuard = Object.freeze({
    logPath: LOG_PATH,
    raizes: RAIZES.lista.slice(),
    raizesAusentes: RAIZES.ausentes,
    blockCode: BLOCK_CODE,
    codigoAborto: CODIGO_ABORTO,
    candidatosDoArgumento,
  });

  if (typeof Module.syncBuiltinESMExports === 'function') Module.syncBuiltinESMExports();
}
