'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const FORA = process.env.VBSS_SONDA_FORA || '';
const DENTRO = process.env.VBSS_SONDA_DENTRO || '';
const FFMPEG = process.env.FFMPEG_PATH || '';
const results = [];

function add(name, ok, detail) {
  results.push({ name, ok: Boolean(ok), detail: String(detail || '').replace(/\s+/g, ' ').trim() });
}

const PREAMBULO = "const fs=require('fs');const cp=require('child_process');const path=require('path');const F=process.env.VBSS_SONDA_FORA;const D=process.env.VBSS_SONDA_DENTRO;const X=process.env.FFMPEG_PATH;";

function sonda(codigo) {
  const r = childProcess.spawnSync(process.execPath, ['-e', 'eval(process.env.VBSS_SONDA_CODIGO)'], {
    env: { ...process.env, VBSS_SONDA_CODIGO: PREAMBULO + codigo },
    encoding: 'utf8',
    timeout: 60000,
  });
  return { status: r.status, out: r.stdout || '', err: r.stderr || '' };
}

function deveBloquear(nome, codigo) {
  const r = sonda(codigo);
  const ok = r.status !== 0 && r.status !== null && !r.out.includes('VAZOU') && r.err.includes('[file-guard] BLOQUEADO');
  add(`bloqueia: ${nome}`, ok, ok ? `codigo ${r.status}; ${r.err.split('\n').find((l) => l.includes('BLOQUEADO')) || ''}` : `codigo ${r.status}; ${r.out.slice(0, 120)} ${r.err.slice(-200)}`);
}

function devePermitir(nome, codigo) {
  const r = sonda(codigo);
  const ok = r.status === 0 && r.out.includes('OK') && !r.err.includes('[file-guard]');
  add(`permite: ${nome}`, ok, ok ? 'codigo 0' : `codigo ${r.status}; ${r.out.slice(0, 120)} ${r.err.slice(-200)}`);
}

function main() {
  const g = globalThis.__vbssFileGuard;
  add('guard de arquivos carregado no processo', Boolean(g), g ? `${g.raizes.length} raizes` : 'ausente');
  add('lista de raizes recebida do render', Boolean(g && !g.raizesAusentes), g && g.raizesAusentes ? 'VBSS_FILE_GUARD_RAIZES ausente' : 'ok');
  if (!FORA || !DENTRO || !FFMPEG || !fs.existsSync(FORA) || !fs.existsSync(DENTRO)) {
    add('arquivos de sonda', false, 'VBSS_SONDA_FORA, VBSS_SONDA_DENTRO e FFMPEG_PATH precisam existir');
    process.stdout.write(JSON.stringify(results));
    return;
  }

  devePermitir('ler arquivo dentro das raizes', "fs.readFileSync(D);console.log('OK')");
  devePermitir('FFmpeg lendo arquivo dentro das raizes', "const r=cp.spawnSync(X,['-v','error','-f','lavfi','-i','anullsrc','-t','0.1','-y',path.join(path.dirname(D),'ok.wav')]);console.log(r.status===0?'OK':'FALHOU '+r.stderr)");
  deveBloquear('fs.readFileSync fora', "fs.readFileSync(F);console.log('VAZOU')");
  deveBloquear('fs.promises.readFile fora', "fs.promises.readFile(F).then(()=>console.log('VAZOU'),()=>{})");
  deveBloquear('fs.readFile (callback) fora', "fs.readFile(F,(e)=>{if(!e)console.log('VAZOU')})");
  deveBloquear('fs.createReadStream fora', "fs.createReadStream(F).on('data',()=>console.log('VAZOU'))");
  deveBloquear('fs.copyFileSync de fora para dentro', "fs.copyFileSync(F,path.join(path.dirname(D),'copia.txt'));console.log('VAZOU')");
  deveBloquear('fs.linkSync (link fisico) de fora para dentro', "fs.linkSync(F,path.join(path.dirname(D),'link.txt'));console.log('VAZOU')");
  deveBloquear('fs.renameSync de fora para dentro', "fs.renameSync(F,path.join(path.dirname(D),'movido.txt'));console.log('VAZOU')");
  deveBloquear('fs.openSync fora', "fs.openSync(F,'r');console.log('VAZOU')");
  deveBloquear('fs.readFileSync com URL file:', "fs.readFileSync(require('url').pathToFileURL(F));console.log('VAZOU')");
  deveBloquear('fs.readFileSync com .. relativo', "process.chdir(path.dirname(D));fs.readFileSync(path.relative(path.dirname(D),F));console.log('VAZOU')");
  deveBloquear('FFmpeg -i com arquivo fora', "cp.spawnSync(X,['-i',F,'-f','null','-']);console.log('VAZOU')");
  deveBloquear('FFmpeg -i com URL file:', "cp.spawn(X,['-i',require('url').pathToFileURL(F).href,'-f','null','-']);console.log('VAZOU')");
  deveBloquear('FFmpeg com lista concat apontando para fora', "const l=path.join(path.dirname(D),'lista.txt');fs.writeFileSync(l,\"file '\"+F.replace(/'/g,\"'\\\\''\")+\"'\\n\");cp.spawnSync(X,['-f','concat','-safe','0','-i',l,'-f','null','-']);console.log('VAZOU')");
  deveBloquear('FFmpeg com filtro amovie apontando para fora', "cp.execFileSync(X,['-f','lavfi','-i','amovie='+F.replace(/\\\\/g,'/').replace(':','\\\\:'),'-f','null','-']);console.log('VAZOU')");
  deveBloquear('FFmpeg com script de filtro apontando para fora', "const s=path.join(path.dirname(D),'graph.txt');fs.writeFileSync(s,'amovie='+F.replace(/\\\\/g,'/').replace(':','\\\\:'));cp.spawnSync(X,['-filter_complex_script',s,'-f','null','-']);console.log('VAZOU')");
  deveBloquear('exec com caminho fora na linha de comando', "cp.execSync('type \"'+F+'\"');console.log('VAZOU')");

  const semRaizes = { ...process.env };
  delete semRaizes.VBSS_FILE_GUARD_RAIZES;
  semRaizes.VBSS_SONDA_CODIGO = `${PREAMBULO}fs.readFileSync(D);console.log('VAZOU')`;
  const r = childProcess.spawnSync(process.execPath, ['-e', 'eval(process.env.VBSS_SONDA_CODIGO)'], { env: semRaizes, encoding: 'utf8', timeout: 60000 });
  add('sem a lista de raizes, recusa ate arquivo do sandbox (falha fechada)', r.status !== 0 && r.status !== null && !r.stdout.includes('VAZOU'), `codigo ${r.status}`);

  process.stdout.write(JSON.stringify(results));
}

try {
  main();
} catch (err) {
  results.push({ name: 'selftest de arquivos', ok: false, detail: err.message });
  process.stdout.write(JSON.stringify(results));
}
