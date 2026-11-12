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

    return k;
  }

  window.MotionKit = { criar, palavras, EASE, DUR };
})();
