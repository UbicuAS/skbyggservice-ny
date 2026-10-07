/* SK Byggservice AS – skript for nettsiden.
   Ingen avhengigheter, ingen kall ut av siden. Alt her er pynt eller
   bekvemmelighet: uten skript står innholdet synlig og lenkene virker. */
(() => {
  "use strict";

  const rot = document.documentElement;
  rot.classList.add("js");
  const reduser = window.matchMedia("(prefers-reduced-motion: reduce)");
  const beroring = window.matchMedia("(hover: none)").matches;
  const lytt = (mq, fn) => {
    if (mq.addEventListener) mq.addEventListener("change", fn);
    else if (mq.addListener) mq.addListener(fn);
  };

  // --- Årstall i bunnen -------------------------------------------------------
  const aar = document.getElementById("aarstall");
  if (aar) aar.textContent = String(new Date().getFullYear());

  // --- Toppfeltet blir massivt når man har rullet -----------------------------
  const topp = document.querySelector(".topp");
  if (topp) {
    const oppdater = () => topp.classList.toggle("er-rullet", window.scrollY > 40);
    window.addEventListener("scroll", oppdater, { passive: true });
    oppdater();
  }

  // --- Mobilmeny --------------------------------------------------------------
  const luke = document.querySelector(".luke");
  const meny = document.getElementById("mobilmeny");
  if (luke && meny) {
    const sett = (aapen) => {
      luke.setAttribute("aria-expanded", String(aapen));
      luke.setAttribute("aria-label", aapen ? "Lukk menyen" : "Åpne menyen");
      meny.classList.toggle("er-aapen", aapen);
      document.body.classList.toggle("meny-aapen", aapen);
      if (aapen) {
        const forste = meny.querySelector("a");
        if (forste) forste.focus();
      }
    };
    luke.addEventListener("click", () => sett(luke.getAttribute("aria-expanded") !== "true"));
    meny.addEventListener("click", (h) => {
      if (h.target instanceof Element && h.target.closest("a")) sett(false);
    });
    document.addEventListener("keydown", (h) => {
      if (h.key === "Escape" && meny.classList.contains("er-aapen")) {
        sett(false);
        luke.focus();
      }
    });
    lytt(window.matchMedia("(min-width: 1061px)"), (h) => {
      if (h.matches) sett(false);
    });
  }

  // --- Animasjoner pauses når de er ute av syne -------------------------------
  // Sparer batteri og gir jevnere rulling på mobil (se .ute-av-syne i stil.css).
  if ("IntersectionObserver" in window) {
    const pause = new IntersectionObserver((oppf) => {
      for (const o of oppf) o.target.classList.toggle("ute-av-syne", !o.isIntersecting);
    });
    document.querySelectorAll(".hero, .baand-ramme").forEach((el) => pause.observe(el));
  }

  // --- Innsig ved rulling -----------------------------------------------------
  const sig = document.querySelectorAll(".sig");
  if ("IntersectionObserver" in window && !reduser.matches) {
    const io = new IntersectionObserver(
      (oppf) => {
        for (const o of oppf) {
          if (o.isIntersecting) {
            o.target.classList.add("synlig");
            io.unobserve(o.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );
    sig.forEach((el) => io.observe(el));
  } else {
    sig.forEach((el) => el.classList.add("synlig"));
  }

  // --- Telleverk --------------------------------------------------------------
  const tellere = document.querySelectorAll("[data-tell]");
  const tell = (el) => {
    const maal = Number.parseInt(el.dataset.tell || "", 10);
    const fra = Number.parseInt(el.dataset.fra || "0", 10);
    if (!Number.isFinite(maal) || !Number.isFinite(fra)) return;
    const varighet = 1600;
    let start = 0;
    const steg = (t) => {
      if (!start) start = t;
      const x = Math.min(1, (t - start) / varighet);
      const myk = 1 - Math.pow(1 - x, 3);
      el.textContent = String(Math.round(fra + (maal - fra) * myk));
      if (x < 1) requestAnimationFrame(steg);
    };
    requestAnimationFrame(steg);
  };
  if (tellere.length && "IntersectionObserver" in window && !reduser.matches) {
    const io = new IntersectionObserver(
      (oppf) => {
        for (const o of oppf) {
          if (o.isIntersecting) {
            tell(o.target);
            io.unobserve(o.target);
          }
        }
      },
      { threshold: 0.6 }
    );
    tellere.forEach((el) => io.observe(el));
  }

  // --- Skjema -----------------------------------------------------------------
  const typeValg = document.getElementById("type");
  document.querySelectorAll("[data-tjeneste]").forEach((a) => {
    a.addEventListener("click", () => {
      if (!(typeValg instanceof HTMLSelectElement)) return;
      const verdi = a.getAttribute("data-tjeneste") || "";
      // bare verdier som faktisk finnes i lista
      if (Array.from(typeValg.options).some((o) => o.value === verdi)) typeValg.value = verdi;
    });
  });

  const skjema = document.getElementById("skjema");
  if (skjema instanceof HTMLFormElement && skjema.dataset.aktiv !== "ja") {
    // Forhåndsvisning: skjemaet har ingen mottaker. Ingenting sendes noe sted.
    skjema.addEventListener("submit", (h) => h.preventDefault());
    const knapp = skjema.querySelector(".skjema__send");
    const status = skjema.querySelector(".skjema__status");
    if (knapp && status) {
      knapp.addEventListener("click", () => {
        if (!skjema.reportValidity()) return;
        status.textContent =
          "Takk! Skjemaet er ikke koblet til ennå i denne forhåndsvisningen, så ingenting ble sendt. " +
          "Ring oss eller send en e-post, så hører du fra oss.";
      });
    }
  }

  // --- Lysboks for prosjektbilder ------------------------------------------------
  // Uten skript (eller uten <dialog>) åpner lenka bare bildet.
  const lysbokser = Array.from(document.querySelectorAll("a.lysboks"));
  if (lysbokser.length && typeof HTMLDialogElement === "function") {
    const dialog = document.createElement("dialog");
    dialog.className = "lysboks-dialog";
    dialog.setAttribute("aria-label", "Prosjektbilde");
    const stort = document.createElement("img");
    stort.alt = "";
    stort.draggable = false; // ellers starter nettleserens egen «dra bildet» og sveipet avbrytes
    stort.addEventListener("dragstart", (h) => h.preventDefault());
    const knapp = (klasse, tegn, etikett) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = klasse;
      b.textContent = tegn;
      b.setAttribute("aria-label", etikett);
      return b;
    };
    const lukk = knapp("lysboks__lukk", "✕", "Lukk bildet");
    const forrige = knapp("lysboks__forrige", "‹", "Forrige bilde");
    const neste = knapp("lysboks__neste", "›", "Neste bilde");
    const teller = document.createElement("p");
    teller.className = "lysboks__teller";
    dialog.append(stort, lukk, forrige, neste, teller);
    document.body.append(dialog);
    let nr = 0;
    const vis = (i) => {
      nr = (i + lysbokser.length) % lysbokser.length;
      const a = lysbokser[nr];
      const lite = a.querySelector("img");
      stort.src = a.getAttribute("href") || "";
      stort.alt = lite ? lite.alt : "";
      teller.textContent = `${nr + 1} / ${lysbokser.length}`;
    };
    let apnetFra = null;
    lysbokser.forEach((a, i) => {
      a.addEventListener("click", (h) => {
        h.preventDefault();
        apnetFra = a;
        vis(i);
        dialog.showModal();
        rot.classList.add("lysboks-aapen");
      });
    });
    dialog.addEventListener("close", () => {
      rot.classList.remove("lysboks-aapen");
      if (apnetFra) apnetFra.focus({ preventScroll: true });
    });
    lukk.addEventListener("click", () => dialog.close());
    forrige.addEventListener("click", () => vis(nr - 1));
    neste.addEventListener("click", () => vis(nr + 1));
    // Sveip til siden for neste/forrige bilde (mobil)
    let start = null;
    let sveipet = false;
    dialog.addEventListener("pointerdown", (h) => {
      start = { x: h.clientX, y: h.clientY };
      sveipet = false;
    });
    dialog.addEventListener("pointerup", (h) => {
      if (!start) return;
      const dx = h.clientX - start.x;
      const dy = h.clientY - start.y;
      start = null;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) {
        sveipet = true;
        vis(dx < 0 ? nr + 1 : nr - 1);
      }
    });
    dialog.addEventListener("click", (h) => {
      if (sveipet) {
        sveipet = false;
        return;
      }
      if (h.target === dialog) dialog.close();
    });
    dialog.addEventListener("keydown", (h) => {
      if (h.key === "ArrowLeft") vis(nr - 1);
      else if (h.key === "ArrowRight") vis(nr + 1);
    });
  }

  // --- Målebåndet ned langs venstre kant --------------------------------------
  // Hver seksjon starter på en hel meter, der etiketten «1m – Tjenester» står.
  // Mellom to meter tegnes 100 cm jevnt fordelt, så skalaen følger siden.
  const maalt = document.querySelector(".maalt");
  if (maalt) {
    const NS = "http://www.w3.org/2000/svg";
    const B = 34; // båndets bredde i px
    const seksjoner = Array.from(maalt.querySelectorAll(":scope > [data-maal]"));
    const maaler = document.querySelector(".maaler");
    const avles = maaler ? maaler.querySelector(".maaler__tall") : null;
    const bred = window.matchMedia("(min-width: 1100px)");
    // Kroken (merkevare/maalebaand-krok.webp) er hektet på bunnen av heroen.
    // Fliken er 4 px tykk, hele kroken 31 px høy. 0 m er ytterkanten av fliken.
    const hero = document.querySelector(".hero");
    const krok = maalt.querySelector(".maalebaand-krok");
    const spor = maalt.querySelector(".maalebaand-spor");
    const FLIK = 4;
    const KROK_H = 31;
    let start = 0; // båndets topp i forhold til .maalt (negativ: oppe ved heroen)
    let baand = null;
    let meterY = [];
    let merker = [];

    const lag = (navn, attr, tekst) => {
      const el = document.createElementNS(NS, navn);
      for (const [k, v] of Object.entries(attr)) el.setAttribute(k, String(v));
      if (tekst !== undefined) el.textContent = tekst;
      return el;
    };

    const tegn = () => {
      if (baand) baand.remove();
      baand = null;
      merker = [];
      if (!bred.matches || seksjoner.length < 2) return;
      // Båndet starter i kroken ved bunnen av heroen (over det oransje båndet).
      // Alle mål under er i båndets egne koordinater: 0 = ytterkanten av fliken.
      start = hero ? hero.getBoundingClientRect().bottom - maalt.getBoundingClientRect().top - FLIK : 0;
      const H = maalt.offsetHeight - start;
      // meterstreken ligger der etiketten står: toppen av seksjonen + polstringen
      const y = seksjoner.map((s) => s.offsetTop + Number.parseFloat(getComputedStyle(s).paddingTop) - start);
      const n = y.length;
      meterY = [0, ...y, y[n - 1] + (y[n - 1] - y[n - 2])];

      baand = lag("svg", { class: "maalebaand", width: B, height: H, viewBox: `0 0 ${B} ${H}`, focusable: "false", "aria-hidden": "true" });
      baand.style.top = `${start}px`;
      if (krok) krok.style.top = `${start}px`;
      // huset tar imot bladet rett under krokplata når båndet er rullet inn
      if (spor) spor.style.top = `${start + KROK_H - 4}px`;
      // samme gulfarge som bladet i bildene (målt); starter under krokplata
      baand.appendChild(lag("rect", { y: KROK_H / 2, width: B, height: H - KROK_H / 2, fill: "#eec720" }));
      let cm = "";
      let halv = "";
      let dm = "";
      const etiketter = lag("g", {
        fill: "#1a1407", "font-family": "Inter, system-ui, sans-serif", "font-size": 8.5, "font-weight": 800, "text-anchor": "middle",
      });
      for (let m = 0; m < meterY.length - 1; m++) {
        const a = meterY[m];
        const steg = (meterY[m + 1] - a) / 100;
        for (let c = 1; c < 100; c++) {
          const yy = a + c * steg;
          if (yy < KROK_H || yy > H) continue; // under kroken synes de ikke uansett
          const t = yy.toFixed(1);
          // streker fra begge kanter og tallene midt på, som på et ekte målebånd
          if (c % 10 === 0) {
            dm += `M0 ${t}H11M${B - 11} ${t}H${B}`;
            etiketter.appendChild(lag("text", { x: B / 2, y: (yy + 3).toFixed(1) }, String(c)));
          } else if (c % 5 === 0) {
            halv += `M0 ${t}H8M${B - 8} ${t}H${B}`;
          } else {
            cm += `M0 ${t}H5M${B - 5} ${t}H${B}`;
          }
        }
      }
      baand.appendChild(lag("path", { d: cm, stroke: "rgba(26,20,7,.6)", "stroke-width": 1 }));
      baand.appendChild(lag("path", { d: halv, stroke: "rgba(26,20,7,.75)", "stroke-width": 1.2 }));
      baand.appendChild(lag("path", { d: dm, stroke: "rgba(26,20,7,.9)", "stroke-width": 1.6 }));
      baand.appendChild(etiketter);
      // hele meter: strek over hele båndet og et merke med «1m», «2m» …
      for (let m = 1; m < meterY.length; m++) {
        const yy = meterY[m];
        if (yy < 0 || yy > H) continue;
        const g = lag("g", { class: "meter" });
        g.appendChild(lag("path", { d: `M0 ${yy.toFixed(1)}H${B}`, stroke: "#1a1407", "stroke-width": 2.5 }));
        g.appendChild(lag("rect", { x: 2, y: (yy + 4).toFixed(1), width: B - 4, height: 15, rx: 2, fill: "#ec671a" }));
        g.appendChild(lag("text", {
          x: B / 2, y: (yy + 15).toFixed(1), "text-anchor": "middle", fill: "#140c05",
          "font-family": "Inter, system-ui, sans-serif", "font-size": 10, "font-weight": 900,
        }, `${m}m`));
        baand.appendChild(g);
        merker[m] = g;
      }
      maalt.prepend(baand);
      les();
    };

    // Avlesning ved kroken midt på skjermen, f.eks. «1,37»
    const les = () => {
      if (!maaler || !avles) return;
      if (!baand) {
        maaler.classList.remove("er-synlig");
        return;
      }
      const r = maalt.getBoundingClientRect();
      const yy = window.innerHeight * 0.5 - r.top - start;
      const inne = yy >= 0 && yy <= r.height - start;
      maaler.classList.toggle("er-synlig", inne);
      if (!inne) return;
      let m = 0;
      while (m < meterY.length - 2 && yy >= meterY[m + 1]) m++;
      const meter = m + (yy - meterY[m]) / (meterY[m + 1] - meterY[m]);
      avles.textContent = Math.max(0, meter).toFixed(2).replace(".", ",");
      merker.forEach((g, i) => {
        if (g) g.classList.toggle("er-aktiv", i === m);
      });
    };

    let venterLes = false;
    window.addEventListener(
      "scroll",
      () => {
        if (venterLes) return;
        venterLes = true;
        requestAnimationFrame(() => {
          venterLes = false;
          les();
        });
      },
      { passive: true }
    );
    let venterTegn = 0;
    const tegnSnart = () => {
      clearTimeout(venterTegn);
      venterTegn = window.setTimeout(tegn, 150);
    };
    if ("ResizeObserver" in window) new ResizeObserver(tegnSnart).observe(maalt);
    window.addEventListener("resize", tegnSnart, { passive: true });
    lytt(bred, tegn);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(tegn);
    tegn();
  }

  // --- Hero: arbeidslys, parallakse og sagflis --------------------------------
  const hero = document.querySelector(".hero");
  const media = hero ? hero.querySelector(".hero__media") : null;
  const lerret = hero ? hero.querySelector(".hero__flis") : null;
  if (!hero || !media) return;

  if (media instanceof HTMLVideoElement && reduser.matches) media.pause();

  // Hvor arbeidslyset står i kildebildet (andel av bredde og høyde), målt i
  // hero-raabygg-v1.png (2688 × 1520).
  const LYS = { x: 0.805, y: 0.512 };
  const KILDE = { b: 2688, h: 1520 };
  let lys = { x: 0, y: 0 };

  const plasserLys = () => {
    const r = hero.getBoundingClientRect();
    const iw = media.naturalWidth || media.videoWidth || KILDE.b;
    const ih = media.naturalHeight || media.videoHeight || KILDE.h;
    const skala = Math.max(r.width / iw, r.height / ih);
    const b = iw * skala;
    const h = ih * skala;
    // object-position i prosent (f.eks. «72% 50%»)
    const pos = getComputedStyle(media).objectPosition.split(" ").map((v) => Number.parseFloat(v) / 100);
    const px = Number.isFinite(pos[0]) ? pos[0] : 0.5;
    const py = Number.isFinite(pos[1]) ? pos[1] : 0.5;
    lys = { x: (r.width - b) * px + LYS.x * b, y: (r.height - h) * py + LYS.y * h };
    hero.style.setProperty("--lys-x", `${lys.x.toFixed(1)}px`);
    hero.style.setProperty("--lys-y", `${lys.y.toFixed(1)}px`);
  };
  plasserLys();
  if (media instanceof HTMLImageElement && !media.complete) media.addEventListener("load", plasserLys, { once: true });

  if (reduser.matches || !(lerret instanceof HTMLCanvasElement)) {
    window.addEventListener("resize", plasserLys, { passive: true });
    return;
  }
  const ctx = lerret.getContext("2d");
  if (!ctx) return;

  // Ferdigtegnet glødende prikk, så hver partikkel bare er en drawImage
  const sprite = document.createElement("canvas");
  sprite.width = sprite.height = 64;
  {
    const s = sprite.getContext("2d");
    if (s) {
      const g = s.createRadialGradient(32, 32, 0, 32, 32, 32);
      g.addColorStop(0, "rgba(255, 226, 170, 1)");
      g.addColorStop(0.25, "rgba(255, 190, 110, .55)");
      g.addColorStop(1, "rgba(255, 150, 60, 0)");
      s.fillStyle = g;
      s.fillRect(0, 0, 64, 64);
    }
  }

  let B = 0;
  let H = 0;
  let dpr = 1;
  let partikler = [];
  const tilfeldig = (a, b) => a + Math.random() * (b - a);

  const ny = (overalt) => {
    const naer = Math.random() < 0.08; // noen få store, uskarpe korn helt foran
    const spredX = Math.max(B, H) * 0.55;
    return {
      x: lys.x + tilfeldig(-spredX, spredX * 0.35),
      y: overalt ? lys.y + tilfeldig(-H * 0.55, H * 0.3) : lys.y + tilfeldig(0, H * 0.35),
      r: naer ? tilfeldig(6, 12) : tilfeldig(0.8, 2.6),
      vx: tilfeldig(-0.22, 0.08) * (naer ? 2.2 : 1),
      vy: tilfeldig(-0.32, -0.06) * (naer ? 2 : 1),
      fase: Math.random() * Math.PI * 2,
      fart: tilfeldig(0.004, 0.012),
      styrke: naer ? tilfeldig(0.08, 0.18) : tilfeldig(0.35, 0.95),
    };
  };

  const tilpass = () => {
    const r = hero.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, beroring ? 1.5 : 2);
    B = r.width;
    H = r.height;
    lerret.width = Math.round(B * dpr);
    lerret.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    plasserLys();
    const antall = Math.max(24, Math.min(beroring ? 45 : 110, Math.round((B * H) / 15000)));
    partikler = Array.from({ length: antall }, () => ny(true));
  };

  // Pekeren gir litt dybde: bildet og flisa beveger seg ulikt (bare med mus)
  const mus = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  let maalX = 0;
  let maalY = 0;
  let naaX = 0;
  let naaY = 0;
  if (mus) {
    hero.addEventListener(
      "pointermove",
      (h) => {
        const r = hero.getBoundingClientRect();
        maalX = (h.clientX - r.left) / r.width - 0.5;
        maalY = (h.clientY - r.top) / r.height - 0.5;
      },
      { passive: true }
    );
    hero.addEventListener("pointerleave", () => {
      maalX = 0;
      maalY = 0;
    });
  }

  let synlig = true;
  let ramme = 0;
  const tegn = () => {
    ramme = 0;
    if (!synlig || document.hidden) return;

    naaX += (maalX - naaX) * 0.05;
    naaY += (maalY - naaY) * 0.05;
    if (mus) {
      media.style.translate = `${(-naaX * 14).toFixed(2)}px ${(-naaY * 10).toFixed(2)}px`;
      lerret.style.translate = `${(naaX * 22).toFixed(2)}px ${(naaY * 16).toFixed(2)}px`;
    }

    ctx.clearRect(0, 0, B, H);
    ctx.globalCompositeOperation = "lighter";
    const rekkevidde = Math.max(B, H) * 0.42;
    for (let i = 0; i < partikler.length; i++) {
      const p = partikler[i];
      p.fase += p.fart;
      p.x += p.vx + Math.sin(p.fase) * 0.18;
      p.y += p.vy + Math.cos(p.fase * 0.7) * 0.06;
      if (p.y < -20 || p.x < -20 || p.x > B + 20) {
        partikler[i] = ny(false);
        continue;
      }
      // sterkest i lyskjeglen, nesten borte utenfor
      const dx = p.x - lys.x;
      const dy = p.y - lys.y;
      const avstand = Math.sqrt(dx * dx + dy * dy) / rekkevidde;
      const glimt = 0.75 + 0.25 * Math.sin(p.fase * 3);
      const a = p.styrke * glimt * (Math.exp(-avstand * avstand * 2.2) + 0.04);
      if (a < 0.01) continue;
      ctx.globalAlpha = Math.min(1, a);
      const d = p.r * 4;
      ctx.drawImage(sprite, p.x - d / 2, p.y - d / 2, d, d);
    }
    ctx.globalAlpha = 1;
    ramme = requestAnimationFrame(tegn);
  };
  const start = () => {
    if (!ramme && synlig && !document.hidden) ramme = requestAnimationFrame(tegn);
  };

  tilpass();
  if ("ResizeObserver" in window) {
    let venter = 0;
    new ResizeObserver(() => {
      clearTimeout(venter);
      venter = window.setTimeout(tilpass, 120);
    }).observe(hero);
  } else {
    window.addEventListener("resize", tilpass, { passive: true });
  }
  // Ingen tegning når heroen er ute av syne eller fanen er skjult
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((oppf) => {
      synlig = oppf[0].isIntersecting;
      start();
    }).observe(hero);
  }
  document.addEventListener("visibilitychange", start);
  lytt(reduser, (h) => {
    if (h.matches) {
      synlig = false;
      ctx.clearRect(0, 0, B, H);
    }
  });
  start();
})();
