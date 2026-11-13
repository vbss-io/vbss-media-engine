(function () {
  const EASE = {
    casa: "power3.out",
    snap: "expo.out",
    troca: "power3.inOut",
    rolagem: "expo.inOut",
    sai: "power2.in",
    respira: "sine.inOut",
    acento: "back.out(1.7)",
  };
  const DUR = { micro: 0.14, rapido: 0.28, base: 0.42, palco: 0.6, lento: 0.9 };

  function palavras(el) {
    const alvo = typeof el === "string" ? document.querySelector(el) : el;
    const spans = [];
    const fatiar = (texto, envolver) => {
      const frag = document.createDocumentFragment();
      texto.split(/(\s+)/).forEach((parte) => {
        if (!parte) return;
        if (/^\s+$/.test(parte)) {
          frag.appendChild(document.createTextNode(" "));
          return;
        }
        const s = document.createElement("span");
        s.className = "k-p";
        s.style.display = "inline-block";
        if (envolver) {
          const interno = envolver.cloneNode(false);
          interno.textContent = parte;
          s.appendChild(interno);
        } else {
          s.textContent = parte;
        }
        spans.push(s);
        frag.appendChild(s);
      });
      return frag;
    };
    Array.from(alvo.childNodes).forEach((no) => {
      if (no.nodeType === 3) alvo.replaceChild(fatiar(no.textContent, null), no);
      else if (no.nodeType === 1 && no.tagName !== "BR") alvo.replaceChild(fatiar(no.textContent, no), no);
    });
    return spans;
  }

  function criar(tl) {
    const k = { EASE, DUR, palavras };

    k.bate = (alvos, t, o = {}) => {
      gsap.set(alvos, { opacity: 0 });
      tl.fromTo(
        alvos,
        { opacity: 0, scale: o.de || 1.6, y: o.y || 0 },
        { opacity: 1, scale: 1, y: 0, duration: o.d || 0.36, ease: EASE.snap, stagger: o.stagger || 0, immediateRender: false },
        t
      );
    };

    k.sobe = (alvos, t, o = {}) => {
      gsap.set(alvos, { opacity: 0 });
      tl.fromTo(
        alvos,
        { opacity: 0, y: o.y || 44 },
        { opacity: 1, y: 0, duration: o.d || DUR.base, ease: EASE.casa, stagger: o.stagger || 0, immediateRender: false },
        t
      );
    };

    k.sai = (alvos, t, o = {}) => {
      tl.to(alvos, { opacity: 0, y: o.y === undefined ? -48 : o.y, x: o.x || 0, duration: o.d || 0.24, ease: EASE.sai, stagger: o.stagger || 0 }, t);
    };

    k.camera = (sel, t, o) => {
      const s = o.s || 1;
      tl.to(sel, { x: o.px - o.fx * s, y: o.py - o.fy * s, scale: s, duration: o.d || 0.8, ease: o.ease || EASE.troca }, t);
    };

    k.cameraVolta = (sel, t, o = {}) => {
      tl.to(sel, { x: 0, y: 0, scale: 1, duration: o.d || 0.6, ease: o.ease || EASE.troca }, t);
    };

    k.foco = (sel, t, caixa, o = {}) => {
      const para = { x: caixa.x, y: caixa.y, width: caixa.w, height: caixa.h, duration: o.d || 0.3, ease: EASE.snap };
      if (o.cor) para.borderColor = o.cor;
      if (o.surge) {
        tl.set(sel, { x: caixa.x, y: caixa.y, width: caixa.w, height: caixa.h }, t);
        tl.fromTo(sel, { opacity: 0, scale: 1.12 }, { opacity: 1, scale: 1, duration: 0.3, ease: EASE.snap, immediateRender: false }, t);
        if (o.cor) tl.set(sel, { borderColor: o.cor }, t);
      } else {
        tl.to(sel, para, t);
      }
    };

    k.marca = (sel, t, o = {}) => {
      gsap.set(sel, { scaleX: 0, transformOrigin: "0% 50%" });
      tl.to(sel, { scaleX: 1, duration: o.d || 0.4, ease: EASE.casa }, t);
    };

    k.toque = (sel, t) => {
      tl.to(sel, { scale: 0.96, duration: 0.1, ease: "power2.out" }, t);
      tl.to(sel, { scale: 1, duration: 0.32, ease: EASE.acento }, t + 0.1);
    };

    k.digita = (valor, cursor, texto, t, d) => {
      tl.set(cursor, { opacity: 1 }, t - 0.3);
      tl.to(valor, { text: texto, duration: d, ease: "none" }, t);
      tl.to(cursor, { opacity: 0, duration: 0.01 }, t + d + 0.35);
    };

    k.respira = (sel, t, total, o = {}) => {
      const periodo = o.periodo || 2.4;
      const voltas = Math.max(1, Math.round(total / periodo));
      const de = {};
      const para = { duration: total / voltas, ease: EASE.respira, yoyo: true, repeat: voltas - 1, immediateRender: false };
      ["x", "y", "rotation", "scale"].forEach((p) => {
        if (o[p] === undefined) return;
        de[p] = p === "scale" ? 1 : -o[p];
        para[p] = p === "scale" ? o[p] : o[p];
      });
      tl.fromTo(sel, de, para, t);
    };

    k.empurra = (sai, entra, t, o = {}) => {
      const largura = o.largura || 720;
      tl.fromTo(entra, { x: largura }, { x: 0, duration: o.d || 0.5, ease: EASE.snap, immediateRender: false }, t);
      tl.to(sai, { x: -largura * 0.3, duration: o.d || 0.5, ease: EASE.snap }, t);
      tl.set(entra, { zIndex: 2 }, t);
      tl.set(sai, { zIndex: 1 }, t);
    };

    k.cortina = (faixas, t, o = {}) => {
      const curso = o.curso || 1700;
      const d = o.d || 0.4;
      const passo = o.passo || 0.07;
      gsap.set(faixas, { x: -curso });
      tl.to(faixas, { x: 0, duration: d, ease: EASE.troca, stagger: passo }, t);
      const lista = gsap.utils.toArray(faixas);
      const troca = t + d + passo * (lista.length - 1);
      tl.to(lista.slice().reverse(), { x: curso, duration: d + 0.05, ease: EASE.troca, stagger: passo }, troca + (o.pausa || 0.05));
      return troca;
    };

    k.legenda = (sel, blocos, o = {}) => {
      const cont = typeof sel === "string" ? document.querySelector(sel) : sel;
      const lista = (Array.isArray(blocos) ? blocos : (blocos && blocos.blocos) || []).filter((b) => b && b.palavras && b.palavras.length);
      if (!cont || !lista.length) return [];
      estiloDaLegenda();
      cont.classList.add("k-legenda");
      const variaveis = { fonte: "--k-leg-fonte", peso: "--k-leg-peso", tamanho: "--k-leg-tamanho", largura: "--k-leg-largura", base: "--k-leg-base", cor: "--k-leg-cor", ativa: "--k-leg-ativa", acento: "--k-leg-acento", contorno: "--k-leg-contorno", espessura: "--k-leg-espessura" };
      Object.keys(variaveis).forEach((nome) => {
        if (o[nome] === undefined) return;
        const valor = typeof o[nome] === "number" && nome !== "peso" ? o[nome] + "px" : String(o[nome]);
        cont.style.setProperty(variaveis[nome], valor);
      });
      const cs = getComputedStyle(cont);
      const lida = (nome, padrao) => cs.getPropertyValue(nome).trim() || padrao;
      const cor = lida("--k-leg-cor", "#FFFFFF");
      const ativa = lida("--k-leg-ativa", "#FFD84D");
      const acento = lida("--k-leg-acento", "#4FE3C1");
      const escala = o.escala || 1.08;
      const entrada = o.entrada || 0.14;
      const antecipa = o.antecipa === undefined ? 0.05 : o.antecipa;
      const folga = o.folga === undefined ? 0.12 : o.folga;
      const emenda = o.emenda === undefined ? 0.3 : o.emenda;
      const linhas = o.linhas || 2;
      const minimo = o.tamanhoMinimo || 44;
      const entradas = lista.map((b, i) => Math.max(i ? lista[i - 1].inicio + 0.01 : 0, b.inicio - antecipa));
      const criados = [];
      lista.forEach((b, i) => {
        const bloco = document.createElement("div");
        bloco.className = "k-leg-bloco";
        const spans = b.palavras.map((p, j) => {
          if (j) bloco.appendChild(document.createTextNode(" "));
          const s = document.createElement("span");
          s.className = p.destaque ? "k-leg-p k-leg-destaque" : "k-leg-p";
          s.textContent = p.texto;
          bloco.appendChild(s);
          return s;
        });
        cont.appendChild(bloco);
        let tamanho = parseFloat(getComputedStyle(bloco).fontSize) || 68;
        const alturaDaLinha = () => parseFloat(getComputedStyle(bloco).lineHeight) || tamanho * 1.14;
        while (bloco.offsetHeight > alturaDaLinha() * linhas + 4 && tamanho > minimo) {
          tamanho -= 4;
          bloco.style.fontSize = tamanho + "px";
        }
        gsap.set(bloco, { autoAlpha: 0 });
        const entra = entradas[i];
        tl.fromTo(
          bloco,
          { autoAlpha: 0, y: o.y === undefined ? 16 : o.y, scale: 0.96 },
          { autoAlpha: 1, y: 0, scale: 1, duration: entrada, ease: EASE.casa, immediateRender: false },
          entra
        );
        const proxima = i + 1 < lista.length ? entradas[i + 1] : null;
        if (proxima !== null && proxima - b.fim <= emenda) tl.set(bloco, { autoAlpha: 0 }, proxima);
        else tl.to(bloco, { autoAlpha: 0, duration: 0.12, ease: EASE.sai }, b.fim + folga);
        b.palavras.forEach((p, j) => {
          const s = spans[j];
          const repouso = p.destaque ? acento : cor;
          const acesa = p.destaque ? acento : ativa;
          const apaga = j + 1 < b.palavras.length ? Math.max(b.palavras[j + 1].inicio, p.inicio + 0.08) : Math.max(p.fim, p.inicio + 0.08);
          gsap.set(s, { color: repouso });
          tl.fromTo(s, { color: repouso, scale: 1 }, { color: acesa, scale: escala, duration: 0.08, ease: "power2.out", immediateRender: false }, Math.max(p.inicio, entra));
          tl.fromTo(s, { color: acesa, scale: escala }, { color: repouso, scale: 1, duration: 0.1, ease: "power2.out", immediateRender: false }, Math.max(apaga, entra + 0.08));
        });
        criados.push(bloco);
      });
      return criados;
    };

    return k;
  }

  function estiloDaLegenda() {
    if (document.getElementById("k-legenda-css")) return;
    const css = [
      '@font-face{font-family:"Inter";src:url("_motor/fonts/inter-900.woff2") format("woff2");font-weight:900;font-style:normal}',
      '@font-face{font-family:"Inter";src:url("_motor/fonts/inter-ext-900.woff2") format("woff2");font-weight:900;font-style:normal;unicode-range:U+0100-024F}',
      ".k-legenda{position:absolute;left:calc((100% - var(--k-leg-largura,800px))/2);width:var(--k-leg-largura,800px);bottom:var(--k-leg-base,24%);height:0;pointer-events:none}",
      '.k-leg-bloco{position:absolute;left:0;right:0;bottom:0;margin:0;text-align:center;text-wrap:balance;font-family:var(--k-leg-fonte,"Inter",sans-serif);font-weight:var(--k-leg-peso,900);font-size:var(--k-leg-tamanho,68px);line-height:1.14;letter-spacing:-.01em;word-spacing:.16em;color:var(--k-leg-cor,#FFFFFF);-webkit-text-stroke:var(--k-leg-espessura,10px) var(--k-leg-contorno,#0B0B14);paint-order:stroke fill;text-shadow:0 6px 0 var(--k-leg-contorno,#0B0B14),0 0 26px rgba(0,0,0,.55);transform-origin:50% 100%}',
      ".k-leg-p{display:inline-block;transform-origin:50% 60%}",
    ].join("");
    const estilo = document.createElement("style");
    estilo.id = "k-legenda-css";
    estilo.textContent = css;
    document.head.appendChild(estilo);
  }

  window.MotionKit = { criar, palavras, EASE, DUR };
})();
