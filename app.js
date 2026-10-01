// 1000×1000 web resource (the Synthetic1000 corpus): a static, hash-routed front end over site/data/ (written by `s1000 site`).
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const REPO = "https://github.com/DynamicsAndNeuralSystems/1000x1000";
const REPO_PUBLIC = true;

const S = { index: null, meta: null, byId: new Map(), fam: new Map(), cls: new Map(), series: new Map(), embed: null };

// ---------- class colours: 14 hues equally spaced in OKLCH, stepped by 5/14 of a turn so neighbours differ ----------
function oklch(L, C, h) {
  const a = C * Math.cos(h * Math.PI / 180), b = C * Math.sin(h * Math.PI / 180);
  const l = (L + .3963377774 * a + .2158037573 * b) ** 3, m = (L - .1055613458 * a - .0638541728 * b) ** 3, s = (L - .0894841775 * a - 1.291485548 * b) ** 3;
  const f = x => { x = Math.max(0, Math.min(1, x)); return Math.round(255 * (x <= .0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - .055)); };
  return `rgb(${f(4.0767416621 * l - 3.3077115913 * m + .2309699292 * s)},${f(-1.2684380046 * l + 2.6097574011 * m - .3413193965 * s)},${f(-.0041960863 * l - .7034186147 * m + 1.707614701 * s)})`;
}
function classColours() {
  const rules = (Lb, Ls, Li, Ld, Cb, Cs, Ci, Cd) => [..."ABCDEFGHIJKLMN"].map((c, k) => {
    const h = (25 + k * 360 * 5 / 14) % 360;
    return `.k-${c}{--cbg:${oklch(Lb, Cb, h)};--csoft:${oklch(Ls, Cs, h)};--cink:${oklch(Li, Ci, h)};--cdot:${oklch(Ld, Cd, h)}}`;
  }).join("");
  const light = rules(.965, .89, .47, .68, .028, .07, .12, .14), dark = rules(.25, .37, .84, .74, .03, .07, .1, .13);
  const el = document.createElement("style");
  el.textContent = light + `@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) ${dark.replace(/}\.k-/g, "} :root:not([data-theme=\"light\"]) .k-")}}`
    + dark.replace(/(^|})\.k-/g, '$1:root[data-theme="dark"] .k-');
  document.head.appendChild(el);
}
const sc = c => S.cls.get(c).short;  // display code (IID, LNG, ...), also used in series IDs; the site keys classes by letter internally
const toCode = x => { const c = S.index.classes.find(k => k.short === x || k.code === x); return c && c.code; };
// the class mascot in a tinted rounded square; size "", "lg" or "xl"
const mascot = (code, size = "") => { const c = S.cls.get(code);
  return c.icon ? `<span class="mascot ${size}" title="${esc(c.short)} · ${esc(c.mascot)}" aria-hidden="true">${c.icon}</span>` : `<span class="letter">${c.short}</span>`; };
const labelTags = r => (r.labels || []).map(l => `<i class="lbl">${esc(l)}</i>`).join("");
// Process sections on a class page: shades of the class hue (hue stepped around it, alternating depth), so
// neighbouring processes look different while the page still reads as one class.
const classHue = code => (25 + "ABCDEFGHIJKLMN".indexOf(code) * 360 * 5 / 14) % 360;
const SHADE = [[0, 0], [16, 1], [-16, 0], [32, 1], [-32, 0], [8, 1], [-8, 0], [24, 1], [-24, 0]];
function shadeVars(code, j) {
  const [dh, deep] = SHADE[j % SHADE.length], h = (classHue(code) + dh + 360) % 360;
  return isDark()
    ? `--cbg:${oklch(deep ? .27 : .24, .035, h)};--csoft:${oklch(.37, .07, h)};--cink:${oklch(deep ? .8 : .86, .1, h)}`
    : `--cbg:${oklch(deep ? .95 : .972, deep ? .035 : .025, h)};--csoft:${oklch(.89, .07, h)};--cink:${oklch(deep ? .42 : .5, .12, h)}`;
}
const cink = el => getComputedStyle(el).getPropertyValue("--cink").trim() || css("--trace");

// "no-cache" revalidates with the server, so a re-export or republish is picked up without a hard reload
async function getJSON(p) { const r = await fetch(p, { cache: "no-cache" }); if (!r.ok) throw new Error(p); return r.json(); }
// Style: "museum" by default (fonts linked in index.html); trials via ?style=classic | field | bench load their fonts here
const STYLE_FONTS = {
  classic: "Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500",
  field: "Young+Serif&family=Source+Sans+3:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500;600",
  bench: "Chivo+Mono:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600",
};
(() => { const st = new URLSearchParams(location.search).get("style");
  if (!STYLE_FONTS[st]) return;
  document.documentElement.dataset.style = st;
  const l = document.createElement("link"); l.rel = "stylesheet";
  l.href = `https://fonts.googleapis.com/css2?family=${STYLE_FONTS[st]}&display=swap`; document.head.appendChild(l); })();

// ---------- visit counts: GoatCounter (anonymous, no cookies), on the live site only ----------
// Each page of the site (#/quiz, #/class/FLOW, ...) and each series opened counts as a view, e.g.
// /1000x1000/#/series/S1000_FLOW_dysts-flow_020. Visit /1000x1000/#toggle-goatcounter once in a browser to stop counting it.
const GC = location.hostname === "dynamicsandneuralsystems.github.io", GC_SITE = "1000x1000";  // the GoatCounter site code
const gcQueue = []; let gcLast = "";
function track(hash = location.hash) {
  if (!GC) return;
  const path = location.pathname + (hash || "#/");
  if (path === gcLast) return; gcLast = path;
  if (window.goatcounter?.count) window.goatcounter.count({ path }); else gcQueue.push(path);
}
if (GC) {
  window.goatcounter = { no_onload: true };
  const s = document.createElement("script");
  s.async = true; s.src = "https://gc.zgo.at/count.js"; s.dataset.goatcounter = `https://${GC_SITE}.goatcounter.com/count`;
  s.onload = () => { while (gcQueue.length) window.goatcounter.count({ path: gcQueue.shift() }); };
  document.head.appendChild(s);
}

async function boot() {
  [S.index, S.meta] = await Promise.all([getJSON("data/index.json"), getJSON("data/meta.json")]);
  classColours();
  // header dropdown: every class, linking to its page
  $("#dd-menu").innerHTML = S.index.classes.map(c => `<a role="menuitem" class="k-${c.code}" href="#/class/${c.short}">${c.icon ? `<span class="mascot sm" aria-hidden="true">${c.icon}</span>` : ""}<b>${c.short}</b><span>${esc(c.name || c.title)}</span></a>`).join("");
  $("#dd-menu").addEventListener("click", () => document.activeElement && document.activeElement.blur());
  for (const r of S.meta) S.byId.set(r.id, r);
  for (const c of S.index.classes) { S.cls.set(c.code, c); for (const f of c.families) S.fam.set(f.name, f); }
  window.addEventListener("hashchange", route);
  route();
}
async function classSeries(c) {
  if (!S.series.has(c)) S.series.set(c, getJSON(`data/series/${c}.json`));
  return S.series.get(c);
}
async function seriesOf(id) { return (await classSeries(S.byId.get(id).cls))[id]; }

// ---------- drawing ----------
function fit(cv) {
  const r = cv.getBoundingClientRect(), d = devicePixelRatio || 1;
  cv.width = Math.max(1, Math.round(r.width * d)); cv.height = Math.max(1, Math.round(r.height * d));
  const g = cv.getContext("2d"); g.setTransform(d, 0, 0, d, 0, 0);
  return [g, r.width, r.height];
}
function range(x) {
  let lo = Infinity, hi = -Infinity;
  for (const v of x) if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; }
  if (!(hi > lo)) { hi = lo + 1; lo -= 1; }
  return [lo, hi];
}
// min/max envelope per pixel column: faithful for 1000 samples in a few hundred pixels
function trace(cv, x, { color = css("--trace"), pad = 3, lw = 1 } = {}) {
  const [g, W, H] = fit(cv);
  const [lo, hi] = range(x), n = x.length;
  const X = i => (i / (n - 1)) * (W - 1), Y = v => pad + (1 - (v - lo) / (hi - lo)) * (H - 2 * pad);
  g.strokeStyle = color; g.lineWidth = lw; g.lineJoin = "round"; g.beginPath();
  if (n <= W * 1.5) {
    x.forEach((v, i) => i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)));
  } else {
    const cols = Math.floor(W);
    let prev = null;
    for (let c = 0; c < cols; c++) {
      const a = Math.floor(c * n / cols), b = Math.max(a + 1, Math.floor((c + 1) * n / cols));
      let mn = Infinity, mx = -Infinity;
      for (let i = a; i < b; i++) { mn = Math.min(mn, x[i]); mx = Math.max(mx, x[i]); }
      const px = c + .5;
      if (prev === null) g.moveTo(px, Y(x[a])); else g.lineTo(px, Y(x[a]));
      g.lineTo(px, Y(mn)); g.lineTo(px, Y(mx)); g.lineTo(px, Y(x[b - 1]));
      prev = c;
    }
  }
  g.stroke();
  return { g, W, H, lo, hi, X, Y };
}

// ---------- sonification ----------
// Waveform: resample so the dominant period (samples) sounds at 220 Hz, loop ~2.5 s with a crossfaded seam.
// Pitch contour: value -> pitch of a sine over two octaves (220-880 Hz), 1000 samples in 4 s.
const Audio = {
  ctx: null, cur: null,
  // 1/f noise is heard best as sound itself (pink-ish noise), not as a pitch contour
  defaultMode(r) { const t = r.tags; return (t.periodic || t.quasiperiodic || t.continuous_time || r.family === "one-over-f-stationary") ? "wave" : "contour"; },
  stop() { if (this.cur) { const c = this.cur; this.cur = null; try { c.node.stop(); } catch {} c.done && c.done(); } },
  play(x, rec, mode, { onpos, done } = {}) {
    this.stop();
    this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
    const ctx = this.ctx, sr = ctx.sampleRate, n = x.length;
    const sorted = [...x].sort((a, b) => a - b), q = p => sorted[Math.floor(p * (n - 1))];
    const lo = q(.01), hi = q(.99) > lo ? q(.99) : lo + 1;
    const out = ctx.createGain(); out.connect(ctx.destination);
    let node, rate, dur, posAt;
    if (mode === "wave") {
      const P = Math.min(Math.max(rec.period || 8, 2), n / 2);
      rate = 220 * P;                          // series samples per second
      dur = 2.5;
      const m = (lo + hi) / 2, s = (hi - lo) / 2;
      const y = x.map(v => Math.max(-1, Math.min(1, (v - m) / s)));
      const F = Math.min(40, Math.floor(n / 4)), L = n - F;  // loop over [F, n) with the tail blended into the head
      const at = p => { const i = Math.floor(p), f = p - i; return y[i] * (1 - f) + y[Math.min(i + 1, n - 1)] * f; };
      const val = p => { if (p >= n - F) { const w = (p - (n - F)) / F; return (1 - w) * at(p) + w * at(p - L); } return at(p); };
      const N = Math.floor(sr * dur), buf = ctx.createBuffer(1, N, sr), d = buf.getChannelData(0), step = rate / sr;
      for (let j = 0; j < N; j++) d[j] = val(F + (j * step) % L);
      node = ctx.createBufferSource(); node.buffer = buf; node.connect(out);
      posAt = t => F + (t * rate) % L;
      out.gain.setValueAtTime(0, ctx.currentTime);
      out.gain.linearRampToValueAtTime(.28, ctx.currentTime + .03);
      out.gain.setValueAtTime(.28, ctx.currentTime + dur - .08);
      out.gain.linearRampToValueAtTime(0, ctx.currentTime + dur);
    } else {
      dur = 4;
      const f = new Float32Array(n);
      x.forEach((v, i) => { const u = Math.max(0, Math.min(1, (v - lo) / (hi - lo))); f[i] = 220 * Math.pow(2, 2 * u); });
      node = ctx.createOscillator(); node.type = "sine";
      node.frequency.setValueCurveAtTime(f, ctx.currentTime, dur);
      node.connect(out);
      posAt = t => Math.min(n - 1, t / dur * n);
      out.gain.setValueAtTime(0, ctx.currentTime);
      out.gain.linearRampToValueAtTime(.2, ctx.currentTime + .03);
      out.gain.setValueAtTime(.2, ctx.currentTime + dur - .06);
      out.gain.linearRampToValueAtTime(0, ctx.currentTime + dur);
    }
    const t0 = ctx.currentTime, me = { node, done };
    node.start(); node.stop(t0 + dur);
    node.onended = () => { if (this.cur === me) { this.cur = null; done && done(); } };
    this.cur = me;
    const tick = () => { if (this.cur !== me) return; onpos && onpos(posAt(ctx.currentTime - t0)); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
    return { rate, dur };
  },
};

// ---------- formatting ----------
const fmt = v => typeof v === "number" ? (Number.isInteger(v) ? String(v) : (Math.abs(v) >= 1e4 || Math.abs(v) < 1e-3 ? v.toExponential(2) : +v.toPrecision(3) + "")) :
  Array.isArray(v) ? "[" + v.map(fmt).join(", ") + "]" : typeof v === "object" && v ? JSON.stringify(v) : String(v);
function paramSummary(p) {
  const e = Object.entries(p || {});
  e.sort((a, b) => (typeof b[1] === "string") - (typeof a[1] === "string"));  // named systems first
  return e.slice(0, 3).map(([k, v]) => typeof v === "string" ? v : `${k} ${fmt(v)}`).join(" · ");
}
const NUM_LABEL = { lyapunov_max: "λ<sub>max</sub>", hurst_H: "Hurst H", arfima_d: "ARFIMA d", spectral_beta: "spectral β",
  period_samples: "period (samples)", timescale_samples: "timescale (samples)", noise_sigma: "noise σ", n_states: "states",
  event_rate: "event rate", burstiness_B: "burstiness B", skewness: "skewness" };
const TAG_TEXT = { reversible: "time-reversible" };
const tagLabel = t => TAG_TEXT[t] || t.replace(/_/g, " ");
// what a tag says, where the name alone could mislead
const TAG_TIP = { reversible: "Time-reversible: the series is statistically the same run backwards (in theory, for an infinitely long record). This needs reversible dynamics and an observed variable the reversal leaves unchanged. Chaotic series can be time-reversible." };
function mathify(el) { if (window.renderMathInElement) renderMathInElement(el, { delimiters: [{ left: "\\(", right: "\\)", display: false }], throwOnError: false }); }

// ---------- views ----------
function setNav(k) { document.querySelectorAll("nav a").forEach(a => a.classList.toggle("on", a.dataset.nav === k)); }

// the header's logo, reused inline in a heading: it reads as "1000×1000" and sits on the text baseline
function logoInline() {
  const svg = $(".brand .logo").cloneNode(true);
  svg.removeAttribute("width"); svg.removeAttribute("height"); svg.removeAttribute("aria-hidden");
  svg.setAttribute("class", "logo-inline"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", "1000×1000");
  return svg.outerHTML;
}
function viewHome() {
  setNav("home");
  const I = S.index, nf = I.classes.reduce((a, c) => a + c.families.length, 0);
  document.body.classList.add("landing");
  $("#view").innerHTML = `
    <section class="land">
      <div class="land-text">
        <h1>The ${logoInline()} collection</h1>
        <div class="land-stats"><span><b>${I.n}</b> series</span><span><b>${I.T}</b> samples each</span><span><b>${nf}</b> families</span><span><b>${I.classes.length}</b> classes</span></div>
        <p>What types of dynamical structure in the world do we as scientists have models for? This website showcases the <b>${I.n}×${I.T} collection</b> (of ${I.n} time series, each ${I.T} samples long). The data were simulated from ${nf} generating mechanisms from across ${I.classes.length} categories (including noise and linear processes, maps, chaotic flows, oscillators, point processes, measurement effects and mathematical models of hearts, brains, climate and ecosystems). You can explore them, download the full dataset, and even listen to them! Have a play?<span class="byline">Developed by <a href="http://www.benfulcher.com/" target="_blank" rel="noopener">Ben Fulcher</a> (<a href="https://dynamicsandneuralsystems.github.io/" target="_blank" rel="noopener">Dynamics and Neural Systems Group</a>, The University of Sydney).</span></p>
        <div class="cta">
          <a class="btn primary" href="#/explore">Explore the zoo <span aria-hidden="true">→</span></a>
          <a class="btn" href="#/map">See the map</a>
        </div>
        <nav class="zoo" aria-label="Classes">${I.classes.map(c => `<a class="pen k-${c.code}" href="#/class/${c.short}" title="${esc(c.short)} · ${esc(c.title)}">${mascot(c.code)}<span><b>${c.short}</b><em>${esc(c.name || c.title)}</em><canvas data-pen="${c.code}"></canvas></span></a>`).join("")}</nav>
      </div>
      <div class="ticker" aria-label="A random stream of series from the corpus"><div class="tstage"></div>
        <div class="tnote">hover to pause · click to open</div></div>
    </section>`;
  document.querySelectorAll("canvas[data-pen]").forEach(cv => {
    const c = S.cls.get(cv.dataset.pen), x = Object.values(c.preview)[0];
    if (x) trace(cv, x.slice(0, 160), { color: cink(cv), pad: 2 });
  });
  startTicker($(".tstage"));
}

function viewExplore() {
  setNav("explore");
  const I = S.index, nf = I.classes.reduce((a, c) => a + c.families.length, 0);
  $("#view").innerHTML = `
    <div class="exhead">
      <div><h1>Explore</h1><p>${I.n} series in ${I.classes.length} classes and ${nf} families. Pick a class to see every series in it.</p></div>
    </div>
    <div class="grid">${I.classes.map(c => `
      <a class="ccard k-${c.code}" href="#/class/${c.short}">
        <div class="row">${mascot(c.code, "lg")}<div><span class="code">${c.short}</span><h3>${esc(c.title)}</h3></div></div>
        <p>${esc(c.blurb)}</p>
        <div class="sparks">${Object.keys(c.preview).map(id => `<canvas data-prev="${c.code}|${id}"></canvas>`).join("")}</div>
        <div class="foot"><span>${c.n} series</span><span>${c.families.length} families</span></div>
      </a>`).join("")}
    </div>`;
  document.querySelectorAll("canvas[data-prev]").forEach(cv => {
    const [c, id] = cv.dataset.prev.split("|");
    trace(cv, S.cls.get(c).preview[id], { color: cink(cv) });
  });
}

// ---------- landing ticker: series rise through a box, fading in at the bottom and out at the top ----------
// Each row shows a WIN-sample window (300) that slides from the start of its series to the end as the row rises,
// so the trace scrolls like a strip chart and finishes just as the row fades out. The y-scale is the whole
// series' range, so the trace does not rescale as the window moves.
const WIN = 300;
function stripSetup(row) {
  const [g, W, H] = fit(row.cv), [lo, hi] = range(row.x);
  Object.assign(row, { g, W, H, lo, hi, color: cink(row.el) });
}
function stripDraw(row, p) {
  const { g, W, H, lo, hi, x } = row, n = x.length, win = Math.min(WIN, n);
  const off = Math.max(0, Math.min(1, p)) * (n - win), pad = 4;
  const X = i => (i - off) / (win - 1) * (W - 1), Y = v => pad + (1 - (v - lo) / (hi - lo)) * (H - 2 * pad);
  g.clearRect(0, 0, W, H);
  g.strokeStyle = row.color; g.lineWidth = 1.1; g.lineJoin = "round"; g.beginPath();
  const i0 = Math.floor(off), i1 = Math.min(n - 1, Math.ceil(off + win - 1));
  for (let i = i0; i <= i1; i++) i === i0 ? g.moveTo(X(i), Y(x[i])) : g.lineTo(X(i), Y(x[i]));
  g.stroke();
}
let tickerRAF = 0;
function stopTicker() { cancelAnimationFrame(tickerRAF); tickerRAF = 0; }
async function startTicker(stage) {
  S.ticker = S.ticker || await getJSON("data/ticker.json");
  if (!stage.isConnected) return;
  const ids = Object.keys(S.ticker), rowH = 68, gap = 14, still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const speed = still ? 0 : 24;  // px per second
  let rows = [], k = Math.floor(Math.random() * ids.length), paused = false, t0 = null;
  const next = () => { const prev = rows.length ? S.byId.get(rows[rows.length - 1].id).cls : "";
    for (let j = 0; j < ids.length; j++) { k = (k + 1 + Math.floor(Math.random() * 5)) % ids.length; if (S.byId.get(ids[k]).cls !== prev) break; }
    return ids[k]; };
  const spawn = y => {
    const id = next(), r = S.byId.get(id), c = S.cls.get(r.cls), el = document.createElement("div");
    el.className = `trow k-${r.cls}`; el.dataset.id = id;
    el.innerHTML = `<div class="tlab">${mascot(r.cls)}<div><b>${esc(r.name)}</b><span class="lbls">${labelTags(r)}</span></div></div><canvas></canvas>`;
    stage.appendChild(el);
    const row = { id, el, y, cv: $("canvas", el), x: S.ticker[id] };
    stripSetup(row);
    stripDraw(row, still ? 0 : prog(y));
    el.onclick = () => openSeries(id);
    row.h = el.offsetHeight || rowH;  // rows grow on narrow screens (label above the trace), so each keeps its own height
    rows.push(row); el.style.transform = `translateY(${y}px)`;
    return row;
  };
  // progress through the box: 0 entering at the bottom, 1 leaving at the top
  const prog = y => (stage.clientHeight - y) / (stage.clientHeight + rowH);
  const H = stage.clientHeight;
  for (let y = still ? 20 : 30; y < H;) y += spawn(y).h + gap;
  stage.onmouseenter = () => { paused = true; }; stage.onmouseleave = () => { paused = false; };
  let refit = false;
  const onResize = () => { refit = true; };
  addEventListener("resize", onResize);
  if (still) return;
  const tick = t => {
    if (!stage.isConnected) { removeEventListener("resize", onResize); return; }
    const dt = t0 == null ? 0 : Math.min(.25, (t - t0) / 1000); t0 = t;
    if (!paused && !$("#modal").open) {
      if (refit) {  // a new width can change row heights: re-stack from the top row
        refit = false; let y = rows.length ? rows[0].y : 0;
        for (const r of rows) { stripSetup(r); r.h = r.el.offsetHeight || rowH; r.y = y; y += r.h + gap; }
      }
      for (const r of rows) { r.y -= speed * dt; r.el.style.transform = `translateY(${r.y}px)`; stripDraw(r, prog(r.y)); }
      while (rows.length && rows[0].y < -rows[0].h) rows.shift().el.remove();
      const last = rows[rows.length - 1];
      if (!last || last.y + last.h <= stage.clientHeight) spawn(last ? last.y + last.h + gap : stage.clientHeight);
    }
    tickerRAF = requestAnimationFrame(tick);
  };
  tickerRAF = requestAnimationFrame(tick);
}

const classState = { chips: new Set(), q: "" };
async function viewClass(code, openId) {
  setNav("explore");
  const c = S.cls.get(code);
  if (!c) return viewExplore();
  const recs = S.meta.filter(r => r.cls === code);
  if ($("#view").dataset.cls !== code) {
    classState.chips.clear(); classState.q = "";
    const codes = S.index.classes.map(k => k.code), k = codes.indexOf(code);
    const tagCount = {};
    for (const r of recs) for (const t of S.index.chip_tags) if (r.tags[t]) tagCount[t] = (tagCount[t] || 0) + 1;
    const doms = {};
    for (const r of recs) if (r.tags.domain && r.tags.domain !== "abstract") doms[r.tags.domain] = (doms[r.tags.domain] || 0) + 1;
    $("#view").dataset.cls = code;
    $("#view").innerHTML = `
      <div class="crumb"><a href="#/explore">Explore</a> / ${c.short}</div>
      <div class="chead k-${code}">
        ${mascot(code, "xl")}
        ${c.icon ? `<span class="wm" aria-hidden="true">${c.icon}</span>` : ""}
        <div><span class="code">${c.short} · the ${esc(c.mascot)}</span><h1>${esc(c.title)}</h1><p>${esc(c.blurb)} ${c.n} series in ${c.families.length} families.</p>${c.motto ? `<p class="motto">${esc(c.motto)}</p>` : ""}</div>
        <div class="cnav">
          <a class="icon" style="display:grid;place-items:center;text-decoration:none" href="#/class/${sc(codes[(k - 1 + codes.length) % codes.length])}" title="Previous class">‹</a>
          <a class="icon" style="display:grid;place-items:center;text-decoration:none" href="#/class/${sc(codes[(k + 1) % codes.length])}" title="Next class">›</a>
        </div>
      </div>
      <div class="filters">
        <input type="search" placeholder="Filter by family, system or parameter" aria-label="Filter series">
        ${Object.entries(tagCount).filter(([, n]) => n < recs.length).sort((a, b) => b[1] - a[1])
          .map(([t, n]) => `<button class="chip" data-tag="${t}" aria-pressed="false"${TAG_TIP[t] ? ` title="${esc(TAG_TIP[t])}"` : ""}>${tagLabel(t)}<span class="n">${n}</span></button>`).join("")}
        ${Object.entries(doms).map(([d, n]) => `<button class="chip" data-tag="domain:${d}" aria-pressed="false">${d}<span class="n">${n}</span></button>`).join("")}
        <span class="count"></span>
      </div>
      ${c.families.map((f, j) => {
        const fr = recs.filter(r => r.family === f.key);
        return `<section class="fam k-${code}" data-fam="${f.key}" style="${shadeVars(code, j)}">
          <div class="fam-h"><i class="fam-dot"></i><h2>${esc(f.label || f.key)}</h2><span class="key">${esc(f.key)}</span><span class="n">${fr.length} series</span>${f.has_card ? "" : `<span class="draft" title="No family card yet: showing the generator docstring">docstring</span>`}</div>
          <div class="fam-sig">${(f.card.equations || []).length ? `<span class="eqi" data-tex="${esc(f.card.equations[0])}"></span>` : ""}<span class="lbls">${(f.labels || []).map(l => `<i class="lbl">${esc(l)}</i>`).join("")}</span></div>
          <p>${esc(f.card.description)}</p>
          <div class="panes">${fr.map(r => `
            <div class="pane" tabindex="0" role="button" data-id="${r.id}" aria-label="${r.id}">
              <div class="lab"><button class="pp" title="Listen" aria-label="Listen to ${r.id}"><span class="tri"></span></button>
                <div><b>${esc(r.name)}</b><span class="lbls">${labelTags(r)}</span>${paramSummary(r.params) ? `<span class="prm" title="${esc(paramSummary(r.params))}">${esc(paramSummary(r.params))}</span>` : ""}</div></div>
              <canvas></canvas>
            </div>`).join("")}</div>
        </section>`;
      }).join("")}`;
    mathify($("#view"));
    if (window.katex) $("#view").querySelectorAll(".eqi[data-tex]").forEach(el => katex.render(el.dataset.tex, el, { displayMode: false, throwOnError: false }));
    const data = await classSeries(code);
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { const p = e.target; trace($("canvas", p), data[p.dataset.id], { color: cink(p) }); io.unobserve(p); }
    }), { rootMargin: "300px" });
    document.querySelectorAll(".pane").forEach(p => io.observe(p));
    $(".filters input").addEventListener("input", e => { classState.q = e.target.value.trim().toLowerCase(); applyFilter(); });
    applyFilter();
  }
  if (pendingFam) { const el = document.querySelector(`.fam[data-fam="${pendingFam}"]`); pendingFam = null; if (el) el.scrollIntoView({ block: "start" }); }
  if (openId) openSeries(openId, false);
}
function onClassClick(e) {
  const chip = e.target.closest(".chip");
  if (chip) {
    const t = chip.dataset.tag, on = chip.getAttribute("aria-pressed") !== "true";
    chip.setAttribute("aria-pressed", on); on ? classState.chips.add(t) : classState.chips.delete(t);
    return applyFilter();
  }
  const pp = e.target.closest(".pp");
  if (pp) {
    const id = pp.closest(".pane").dataset.id, r = S.byId.get(id);
    if (pp.classList.contains("on")) return Audio.stop();
    seriesOf(id).then(x => {
      pp.classList.add("on");
      Audio.play(x, r, Audio.defaultMode(r), { done: () => pp.classList.remove("on") });
    });
    return;
  }
  const pane = e.target.closest(".pane");
  if (pane) openSeries(pane.dataset.id);
}
function matches(r) {
  for (const t of classState.chips) {
    if (t.startsWith("domain:")) { if (r.tags.domain !== t.slice(7)) return false; }
    else if (!r.tags[t]) return false;
  }
  if (classState.q) {
    const hay = (r.name + " " + (r.labels || []).join(" ") + " " + r.family + " " + r.id + " " + JSON.stringify(r.params)).toLowerCase();
    if (!hay.includes(classState.q)) return false;
  }
  return true;
}
function applyFilter() {
  let shown = 0, total = 0;
  document.querySelectorAll(".fam").forEach(sec => {
    let k = 0;
    sec.querySelectorAll(".pane").forEach(p => { const ok = matches(S.byId.get(p.dataset.id)); p.hidden = !ok; k += ok; total++; });
    sec.hidden = !k; shown += k;
  });
  const el = $(".count"); if (el) el.textContent = shown === total ? `${total} series` : `${shown} of ${total} series`;
}

// ---------- series modal ----------
let modalId = null, modalList = [];
// The family card's notation list describes the card's generic equation. A series that shows its own explicit
// equations (r.eqs) keeps only the clauses whose symbols appear in them, plus a line naming its state variables;
// otherwise the list would define symbols (u, f, u_c, ...) that are nowhere on screen.
// the symbols a TeX string uses: letters and commands (greek, bold) with any subscript; operators and text are ignored
const TEX_OPS = /^\\(frac|tfrac|dfrac|left|right|dot|ddot|sqrt|sum|prod|int|cdot|quad|qquad|lfloor|rfloor|lceil|rceil|begin|end|mathcal|mathbb|ln|log|exp|sin|cos|tan|tanh|min|max|bmod|pmod|infty|partial|to|le|ge|leq|geq|ne|neq|approx|sim|in|notin|mid|pm|mp|times|underset|overset|xrightarrow|rightleftharpoons|varnothing|Rightarrow|leftarrow|hat|bar|tilde|textstyle|displaystyle|lim|det|mathrm|operatorname|text|binom|choose|lvert|rvert|langle|rangle)$/;
function texSyms(t) {
  t = t.replace(/\\(text|mathrm|operatorname)\{[^{}]*\}/g, " ");
  const out = [], re = /(\\mathbf\{\\?[A-Za-z]+\}|\\boldsymbol\{\\?[A-Za-z]+\}|\\[A-Za-z]+|[A-Za-z])(\s*_\s*(\{[^{}]*\}|[A-Za-z0-9]))?/g;
  for (const m of t.matchAll(re)) {
    const base = m[1].replace(/\s/g, ""); if (TEX_OPS.test(base)) continue;
    out.push({ base, full: m[3] ? `${base}_${m[3].replace(/[{}\s]/g, "")}` : base });
  }
  return out;
}
function whereFor(r, card) {
  const where = card.where || [];
  if (!r.eqs) return where;
  const eqT = new Set(texSyms(r.eqs.lines.join(" ") + " " + Object.keys(r.eqs.params || {}).join(" ")).flatMap(t => [t.base, t.full]));
  const covered = new Set();
  const kept = where.map(line => line.split(/;\s+/).filter(cl => {
    const head = cl.indexOf("\\):") >= 0 ? cl.slice(0, cl.indexOf("\\):") + 2) : cl;
    const syms = [...head.matchAll(/\\\((.+?)\\\)/g)].flatMap(m => m[1].split(/,\s*/)).map(x => texSyms(x)[0]).filter(Boolean);
    // a clause labelled for some members of the family ("Brusselator: ...", "Rössler and Chua: ...") belongs only to them
    const label = cl.match(/^([A-Z][^:\\]{2,30}):\s/);
    if (label && !label[1].split(/,\s*|\s+and\s+/).some(m => r.name.toLowerCase().includes(m.trim().toLowerCase()))) return false;
    if (!syms.length) return !/each series|shown with it|for each series/i.test(cl);
    const ok = syms.some(sy => eqT.has(sy.full) || (sy.full === sy.base && eqT.has(sy.base)));
    if (ok) syms.forEach(sy => covered.add(sy.full));
    return ok;
  }).join("; ")).filter(Boolean);
  // name the state variables if no kept clause does: dx/dt left-hand sides (flows) or x_{n+1} ones (maps)
  const texOf = t => t.full === t.base ? t.base : `${t.base}_{${t.full.slice(t.base.length + 1)}}`;
  const flow = [...new Set(r.eqs.lines.flatMap(l => [...l.matchAll(/\\dot\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\\mathbf\{[A-Za-z]\}|[A-Za-z])(\s*_\s*(\{[^{}]*\}|[A-Za-z0-9]))?/g)]
    .map(m => { const t = texSyms((m[1].startsWith("{") ? m[1].slice(1, -1) : m[1]) + (m[2] || ""))[0]; return t ? texOf(t) : null; }).filter(Boolean)))];
  const map = [...new Set(r.eqs.lines.map(l => (l.match(/^\s*([A-Za-z])_\{\s*n\s*\+\s*1\s*\}/) || [])[1]).filter(Boolean))].map(v => `${v}_n`);
  const vars = flow.length ? flow : map;
  if (vars.length && !vars.every(v => covered.has(texSyms(v)[0]?.full) || covered.has(texSyms(v)[0]?.base)))
    kept.unshift(flow.length ? `\\(${vars.join(", ")}\\): the state variable${vars.length > 1 ? "s" : ""}; a dot is the time derivative`
      : `\\(${vars.join(", ")}\\): the state at iteration \\(n\\), one sample per iteration`);
  return kept;
}
async function openSeries(id, push = true) {
  const r = S.byId.get(id); if (!r) return;
  mwStop();
  const dlg = $("#modal");
  modalId = id; zoom = null;
  track(`#/series/${id}`);
  // prev/next walk the currently visible panes if on a class page, else the whole class
  const vis = [...document.querySelectorAll(".pane")].filter(p => !p.hidden && !p.closest("[hidden]")).map(p => p.dataset.id);
  modalList = vis.includes(id) ? vis : S.meta.filter(m => m.cls === r.cls).map(m => m.id);
  const home = !/^#\/(class|map)/.test(location.hash);
  if (push && !home) {
    const base = location.hash.startsWith("#/map") ? "#/map" : `#/class/${sc(r.cls)}`;
    try { history.replaceState(null, "", `${base}/${id}`); } catch {}
  }
  const f = S.fam.get(`${r.cls}.${r.family}`), card = f.card, c = S.cls.get(r.cls);
  dlg.className = `k-${r.cls}`;
  $("#m-kicker").innerHTML = `<span class="letter sm">${c.short}</span><a href="#/class/${c.short}">${esc(c.title)}</a> · family <b>${esc(r.family)}</b>, instance ${r.index} of ${f.n} · <span class="mono">${r.id}</span>`;
  $("#m-title").textContent = r.name;
  $("#m-family").innerHTML = `
    <h3>The process</h3>
    <p>${esc(r.about || card.description)}</p>
    ${!r.eqs && card.equations ? `<h3>Equations</h3><div class="eq">${card.equations.map(e => `<div data-tex="${esc(e)}"></div>`).join("")}</div>` : ""}
    ${r.eqs ? `<h3>Equations</h3><div class="eq">
        <div data-tex="${esc(`\\begin{aligned}${r.eqs.lines.join(" \\\\ ")}\\end{aligned}`)}"></div></div>
        ${Object.keys(r.eqs.params).length ? `<p class="eq-params">with ${Object.entries(r.eqs.params).map(([k, v]) => `<span data-itex="${esc(`${k} = ${+v.toPrecision(4)}`)}"></span>`).join(", ")}${r.eqs.note ? ". " + esc(r.eqs.note) : ""}</p>` : r.eqs.note ? `<p class="eq-params">${esc(r.eqs.note)}</p>` : ""}`
      : (["dysts-flow", "dysts-flow-coarse", "dysts-flow-extra", "dysts-map"].includes(r.family)
        ? `<p class="nocard">This system's equations are written in vector form in <a href="https://github.com/williamgilpin/dysts">dysts</a> and are not shown explicitly here.</p>` : "")}
    ${whereFor(r, card).length ? `<ul class="where">${whereFor(r, card).map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
    ${r.about && card.description ? `<h3>The family</h3><p>${esc(card.description)}</p>` : ""}
    ${card.fixed ? `<h3>Fixed settings <span class="h3-sub">(all series in this family)</span></h3><ul class="where">${card.fixed.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
    ${card.simulation ? `<h3>Family simulation details</h3><p>${esc(card.simulation)}</p>` : ""}
    ${card.references ? `<h3>References</h3><ol class="refs">${card.references.map(x => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}
    ${f.has_card ? "" : `<p class="nocard">No family card yet: this is the generator's docstring. Equations and references to come.</p>`}
    <h3>Regenerate</h3>
    <pre class="cli">s1000 build --profile ${S.index.release || S.index.profile} --family ${r.cls}.${r.family}
# instance ${r.index} · seed name ${r.seed_name}</pre>
    <p style="margin-top:8px;font-size:13px"><a href="#" data-feedback="${r.id}">Feedback on this series</a> · ${REPO_PUBLIC ? `<a href="${REPO}/blob/main/${f.source}">Generator source</a>` : "Generator source"} <span class="mono" style="color:var(--ink-3)">${esc(f.source)}</span></p>`;
  const tags = Object.entries(r.tags).filter(([k]) => k !== "stationary" && k !== "domain");
  const nums = Object.entries(r.nums);
  const params = Object.entries(r.params);
  $("#m-instance").innerHTML = `
    ${params.length ? `<h3>This series' parameters</h3><table class="kv">${params.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(fmt(v))}</td></tr>`).join("")}</table>` : ""}
    <h3>Properties</h3>
    <div class="tags">${tags.map(([k, v]) => `<span class="tag ${v === "partly" ? "partly" : ""}" title="${esc(TAG_TIP[k] || `${k}: ${v}`)}">${tagLabel(k)}${v === "partly" ? " (partly)" : ""}</span>`).join("")}
      <span class="tag">${esc(r.tags.domain || "abstract")}</span></div>
    ${nums.length ? `<h3>Ground truth</h3><table class="kv">${nums.map(([k, v]) => `<tr><td>${NUM_LABEL[k] || k}</td><td>${fmt(v)}</td></tr>`).join("")}</table>` : ""}
    <h3>Sample statistics</h3>
    <table class="kv"><tr><td>mean</td><td>${fmt(r.mean)}</td></tr><tr><td>s.d.</td><td>${fmt(r.sd)}</td></tr>
      ${r.peak ? `<tr><td>dominant period</td><td>${fmt(r.period)} samples</td></tr>` : ""}</table>
    <h3>Seed</h3>
    <table class="kv"><tr><td>name</td><td>${esc(r.seed_name)}</td></tr><tr><td>seed</td><td>${r.seed}</td></tr></table>`;
  if (window.katex) {
    $("#m-family").querySelectorAll("[data-tex]").forEach(el => katex.render(el.dataset.tex, el, { displayMode: true, throwOnError: false }));
    $("#m-family").querySelectorAll("[data-itex]").forEach(el => katex.render(el.dataset.itex, el, { displayMode: false, throwOnError: false }));
  }
  mathify($("#m-family"));
  const def = Audio.defaultMode(r);
  dlg.querySelectorAll(".play").forEach(b => { b.classList.toggle("default", b.dataset.mode === def); b.classList.remove("on"); });
  $("#m-play-hint").textContent = `default audio for this series: ${def === "wave" ? "waveform" : "pitch contour"}`;
  Audio.stop();
  if (!dlg.open) dlg.showModal();
  $("#m-nbrs").innerHTML = "";
  const x = await seriesOf(id);
  if (modalId !== id) return;
  drawModal(x);
  requestAnimationFrame(() => {
    if (modalId !== id) return;
    document.querySelectorAll("#m-psk button").forEach(b => b.onclick = () => { psKind = b.dataset.k; renderPhaseSpace(x, r.step); });
    renderPhaseSpace(x, r.step);
  });
  renderNeighbours(id);
}
// Recurrence plot: delay-embed the z-scored series in m = 3 dimensions with tau the lag where the
// autocorrelation first drops below 1/e, and mark pairs of states closer than the distance giving a 10%
// recurrence rate. Drawn at about 300 px: each pixel is shaded by the fraction of recurrent pairs it covers.
// Phase portrait: the delay plot x_t against x_{t+tau} (same tau as the recurrence plot), one dot per pair over a faint line in time order.
function phasePortrait(cv, x, color, tau) {
  const [g, W, H] = fit(cv), [lo, hi] = range(x), n = x.length, pad = 18;
  const X = v => pad + (v - lo) / (hi - lo) * (W - 2 * pad), Y = v => H - pad - (v - lo) / (hi - lo) * (H - 2 * pad);
  g.strokeStyle = css("--line"); g.lineWidth = 1; g.strokeRect(pad, pad, W - 2 * pad, H - 2 * pad);
  g.fillStyle = css("--ink-3"); g.font = "italic 11px Inter, sans-serif";
  g.fillText("x(t)", W / 2 - 10, H - 4); g.save(); g.translate(11, H / 2 + 16); g.rotate(-Math.PI / 2); g.fillText("x(t + τ)", 0, 0); g.restore();
  // zero lines where 0 is in range, and the axis extent at each end, so the portrait has a scale
  g.save(); g.strokeStyle = css("--ink-3"); g.globalAlpha = .45; g.lineWidth = 1; g.setLineDash([3, 3]); g.beginPath();
  if (lo < 0 && hi > 0) { g.moveTo(X(0), pad); g.lineTo(X(0), H - pad); g.moveTo(pad, Y(0)); g.lineTo(W - pad, Y(0)); }
  g.stroke(); g.restore();
  g.font = "10px Inter, sans-serif"; g.fillStyle = css("--ink-3"); const f = v => Math.abs(v) >= 1e4 || (v !== 0 && Math.abs(v) < 1e-2) ? v.toExponential(1) : +v.toPrecision(3);
  g.textAlign = "left"; g.fillText(f(lo), pad, H - pad + 11); g.textAlign = "right"; g.fillText(f(hi), W - pad, H - pad + 11);
  g.save(); g.translate(pad - 4, H - pad); g.rotate(-Math.PI / 2); g.textAlign = "left"; g.fillText(f(lo), 0, 0); g.textAlign = "right"; g.fillText(f(hi), H - 2 * pad, 0); g.restore();
  if (lo < 0 && hi > 0) { g.textAlign = "center"; g.fillText("0", X(0), H - pad + 11); }
  g.textAlign = "left";
  g.strokeStyle = color; g.globalAlpha = .15; g.lineWidth = .5; g.lineJoin = "round"; g.beginPath();  // faint trajectory
  for (let i = 0; i + tau < n; i++) i ? g.lineTo(X(x[i]), Y(x[i + tau])) : g.moveTo(X(x[i]), Y(x[i + tau]));
  g.stroke();
  g.fillStyle = color; g.globalAlpha = .55;
  for (let i = 0; i + tau < n; i++) { g.beginPath(); g.arc(X(x[i]), Y(x[i + tau]), 1.6, 0, 7); g.fill(); }
  g.globalAlpha = 1;
}
function acfTau(x) {
  const n = x.length, mu = x.reduce((a, b) => a + b, 0) / n, sd = Math.sqrt(x.reduce((a, b) => a + (b - mu) ** 2, 0) / n) || 1;
  const z = x.map(v => (v - mu) / sd);
  for (let k = 1; k < 40; k++) { let c = 0; for (let i = 0; i + k < n; i++) c += z[i] * z[i + k]; if (c / n < 1 / Math.E) return k; }
  return 40;
}
let psKind = "phase";
// A series that iterates a discrete-time rule (a map) uses the rule's own step, tau = 1; others the ACF delay.
function renderPhaseSpace(x, step) {
  const cv = $("#m-rp"), col = MW.on && MW.glow ? "rgb(90, 255, 70)" : cink(cv), tau = step || acfTau(x);
  MW.sz.v = null;
  const why = step ? "one iteration of the map" : "where the autocorrelation drops below 1/e";
  document.querySelectorAll("#m-psk button").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === psKind));
  if (psKind === "phase") {
    phasePortrait(cv, x, col, tau);
    $("#m-rp-note").textContent = step
      ? `Each point pairs the value now with the next one (τ = 1, one iteration of the map), so a deterministic map traces its own graph; noise blurs it into a cloud.`
      : `Each point pairs the value now with the value τ = ${tau} samples later (τ ${why}). Loops and sheets suggest deterministic dynamics; a round cloud suggests noise.`;
  } else if (psKind === "spec") {
    spectrum(cv, x, col);
    $("#m-rp-note").textContent = `Welch power spectrum: Hann-windowed 256-sample segments with 50% overlap, log–log, frequency in cycles per sample. The dashed line is white noise of the same variance: a flat spectrum means no linear memory, a falling one long-range correlation, peaks periodicity.`;
  } else {
    const [g] = fit(cv); g.setTransform(1, 0, 0, 1, 0, 0);
    recurrence(cv, x, col, tau);
    $("#m-rp-note").textContent = `Delay embedding m = 3, τ = ${tau} (${why}); shaded where two states are within the 10% recurrence radius. Diagonal lines mean determinism, checkerboards regime changes, isolated dots noise.`;
  }
}

// Welch power spectrum: Hann-windowed segments of 256 samples, 50% overlap, each mean-removed; the average
// |X_k|^2 / sum(w^2), so white noise of variance s^2 sits flat at s^2 (drawn dashed for reference)
const WELCH = new WeakMap();
function welch(x, L = 256) {
  if (WELCH.has(x)) return WELCH.get(x);
  const n = x.length, w = Float64Array.from({ length: L }, (_, i) => .5 - .5 * Math.cos(2 * Math.PI * i / (L - 1)));
  const ww = w.reduce((a, v) => a + v * v, 0), P = new Float64Array(L / 2 + 1); let segs = 0;
  const re = new Float64Array(L), im = new Float64Array(L);
  for (let s0 = 0; s0 + L <= n; s0 += L / 2) {
    let m = 0; for (let i = 0; i < L; i++) m += x[s0 + i]; m /= L;
    for (let i = 0; i < L; i++) { re[i] = (x[s0 + i] - m) * w[i]; im[i] = 0; }
    fft(re, im);
    for (let k = 0; k <= L / 2; k++) P[k] += (re[k] * re[k] + im[k] * im[k]) / ww;
    segs++;
  }
  const mu = x.reduce((a, v) => a + v, 0) / n, v = x.reduce((a, u) => a + (u - mu) ** 2, 0) / n;
  const out = { f: Array.from({ length: L / 2 }, (_, k) => (k + 1) / L), P: Array.from(P.slice(1), p => p / segs), white: v };
  WELCH.set(x, out); return out;
}
function fft(re, im) {  // in-place radix-2
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) { let b = n >> 1; for (; j & b; b >>= 1) j ^= b; j ^= b; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let len = 2; len <= n; len <<= 1) {
    const a = -2 * Math.PI / len, wr = Math.cos(a), wi = Math.sin(a);
    for (let i = 0; i < n; i += len) { let cr = 1, ci = 0;
      for (let j = 0; j < len / 2; j++) {
        const ur = re[i + j], ui = im[i + j], vr = re[i + j + len / 2] * cr - im[i + j + len / 2] * ci, vi = re[i + j + len / 2] * ci + im[i + j + len / 2] * cr;
        re[i + j] = ur + vr; im[i + j] = ui + vi; re[i + j + len / 2] = ur - vr; im[i + j + len / 2] = ui - vi;
        const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
      }
    }
  }
}
function spectrum(cv, x, color, { axis = css("--ink-3"), grid = css("--line"), glow = null } = {}) {
  const [g, W, H] = fit(cv), { f, P, white } = welch(x), pad = 18, padL = 34;  // left pad: room for the power labels
  const lp = P.map(p => Math.log10(Math.max(p, 1e-300))), lw = Math.log10(white);
  let lo = Math.min(...lp, lw), hi = Math.max(...lp, lw); lo = Math.floor(lo - .1); hi = Math.ceil(hi + .1);
  const fl = Math.log10(f[0]), fh = Math.log10(.5);
  const X = v => padL + (Math.log10(v) - fl) / (fh - fl) * (W - padL - pad), Y = l => H - pad - (l - lo) / (hi - lo) * (H - 2 * pad);
  g.strokeStyle = grid; g.lineWidth = 1; g.strokeRect(padL, pad, W - padL - pad, H - 2 * pad);
  g.fillStyle = axis; g.font = "10px Inter, sans-serif"; g.textAlign = "center";
  for (const v of [.01, .1, .5]) if (v >= f[0]) { g.fillText(v, X(v), H - pad + 11); g.globalAlpha = .35; g.beginPath(); g.moveTo(X(v), pad); g.lineTo(X(v), H - pad); g.strokeStyle = grid; g.stroke(); g.globalAlpha = 1; }
  const step = Math.max(1, Math.ceil((hi - lo) / 5));
  g.save(); g.textAlign = "right";
  const sup = e => String(e).replace(/-/g, "⁻").replace(/\d/g, d => "⁰¹²³⁴⁵⁶⁷⁸⁹"[d]);
  for (let e = Math.ceil(lo); e <= hi; e += step) g.fillText(`10${sup(e)}`, padL - 3, Y(e) + 3);
  g.restore();
  g.font = "italic 11px Inter, sans-serif"; g.fillText("frequency", (W + padL - pad) / 2, H - 1);
  g.save(); g.translate(8, H / 2); g.rotate(-Math.PI / 2); g.fillText("power", 0, 0); g.restore();
  g.save(); g.strokeStyle = axis; g.globalAlpha = .6; g.setLineDash([4, 3]); g.beginPath(); g.moveTo(padL, Y(lw)); g.lineTo(W - pad, Y(lw)); g.stroke(); g.restore();
  if (glow) { g.shadowColor = glow; g.shadowBlur = 9; }
  g.strokeStyle = color; g.lineWidth = 1.4; g.lineJoin = "round"; g.beginPath();
  f.forEach((v, k) => k ? g.lineTo(X(v), Y(lp[k])) : g.moveTo(X(v), Y(lp[k]))); g.stroke(); g.shadowBlur = 0;
  g.textAlign = "left";
}
function recurrence(cv, x, color, tau) {
  const n = x.length, mu = x.reduce((a, b) => a + b, 0) / n;
  const sd = Math.sqrt(x.reduce((a, b) => a + (b - mu) ** 2, 0) / n) || 1, z = x.map(v => (v - mu) / sd);
  const m = 3, N = n - (m - 1) * tau, d = (i, j) => { let s = 0; for (let k = 0; k < m; k++) { const u = z[i + k * tau] - z[j + k * tau]; s += u * u; } return s; };
  const sample = []; for (let s = 0; s < 20000; s++) sample.push(d(Math.floor(Math.random() * N), Math.floor(Math.random() * N)));
  sample.sort((a, b) => a - b); const eps = sample[Math.floor(.1 * sample.length)];
  const B = Math.max(1, Math.ceil(N / 300)), P = Math.ceil(N / B), cnt = new Float32Array(P * P);
  for (let i = 0; i < N; i++) for (let j = i; j < N; j++) if (d(i, j) <= eps) {
    const a = Math.floor(i / B), b = Math.floor(j / B); cnt[a * P + b]++; if (a !== b) cnt[b * P + a]++;
  }
  cv.width = P; cv.height = P;
  const g = cv.getContext("2d"), img = g.createImageData(P, P), px = img.data;
  const [cr, cg, cb] = (color.match(/\d+/g) || [30, 30, 30]).map(Number);
  for (let a = 0; a < P; a++) for (let b = 0; b < P; b++) {
    const f = cnt[a * P + b] / (B * B); if (!f) continue;
    const o = ((P - 1 - a) * P + b) * 4;
    px[o] = cr; px[o + 1] = cg; px[o + 2] = cb; px[o + 3] = Math.round(255 * Math.min(1, Math.pow(f * 2.2, .75)));
  }
  g.putImageData(img, 0, 0);
  return tau;
}

async function renderNeighbours(id) {
  S.nbrs = S.nbrs || await getJSON("data/neighbours.json");
  const list = S.nbrs.nn[id] || [];
  if (modalId !== id || !list.length) return;
  const el = $("#m-nbrs");
  el.innerHTML = `<h3>Similar dynamics <span>nearest ${list.length} series in ${esc(S.nbrs.features)} feature space</span></h3>
    <div class="nbrs">${list.map(([j]) => { const r = S.byId.get(j);
      return `<button class="nb k-${r.cls}" data-id="${j}" title="${j}"><div class="nb-lab"><span class="letter sm">${sc(r.cls)}</span><b>${esc(r.name)}</b></div><canvas></canvas></button>`; }).join("")}</div>`;
  // after the new series has rendered, bring the top of the pop-up (its trace) back into view
  el.querySelectorAll(".nb").forEach(b => b.onclick = () => openSeries(b.dataset.id).then(() => {
    const d = $("#modal");
    d.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    setTimeout(() => { if (d.scrollTop > 0) d.scrollTop = 0; }, 600);  // where smooth scrolling is unavailable
  }));
  await Promise.all(list.map(async ([j]) => {
    const xj = await seriesOf(j), b = el.querySelector(`.nb[data-id="${j}"]`);
    if (modalId === id && b) trace($("canvas", b), xj, { color: cink(b) });
  }));
}
// ---------- the worm in the series pop-up ----------
// Worm (off by default) sets a worm crawling along the pop-up's series in journey view: the plot's zoom follows it
// (200 samples around its head); turning it off returns to the whole series. Glow darkens the plot and the
// phase-space panel so only its fading trail shows.
const MW = { on: false, journey: false, glow: false, wormAt: 0, run: 0, trail: [], sz: { v: null } };
function mwSpan() { const n = modalX.length, a = Math.max(0, Math.min(n - 1 - 200, Math.round(MW.wormAt) - 100)); return [a, a + 200]; }
function mwSync() {
  const on = MW.on;
  $("#m-worm").setAttribute("aria-pressed", on); $("#m-wormopts").hidden = !on;
  $("#m-glow").setAttribute("aria-pressed", MW.glow);
  $("#modal .m-plot").classList.toggle("glowing", on && MW.glow); $("#m-ps").classList.toggle("glowing", on && MW.glow);
  if (!(on && MW.journey) && MW.zoomed) { zoom = null; MW.zoomed = false; }
  if (modalX) { drawModal(modalX); renderPhaseSpace(modalX, S.byId.get(modalId).step); }
  MW.sz.v = null;
  discoSync();
}
function mwStop() {
  if (!MW.on) return;
  MW.on = false; MW.journey = false; MW.run++;
  for (const id of ["#m-wormcv", "#m-rpov"]) { const c = $(id); c.getContext("2d").clearRect(0, 0, c.width, c.height); }
  mwSync();
}
function mwStart() {
  if (!modalX || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  // resume where it stopped on this series; a new series starts from its beginning (or the current zoom's left edge)
  if (MW.sid !== modalId) { MW.sid = modalId; MW.wormAt = zoom ? zoom[0] : 0; }
  MW.on = true; MW.journey = true; MW.run++; MW.trail = [];
  const x = modalX, r = S.byId.get(modalId), tau = r.step || acfTau(x);
  mwSync();
  qworm($("#m-wormcv"), x, () => {
    if (!MW.on || modalX !== x || !modalPlot) return null;
    if (MW.journey) { const sp = mwSpan(); if (!zoom || zoom[0] !== sp[0]) { zoom = sp; MW.zoomed = true; drawModal(x); } }
    wormPov($("#m-rpov"), $("#m-rp"), x, tau, { view: psKind, glow: MW.glow, gone: false, trail: MW.trail, at: MW.wormAt, sz: MW.sz });
    const [a, b] = zoom || [0, x.length - 1];
    return { a, b, X: modalPlot.X, Y: modalPlot.Y };
  }, 1, false, () => MW.glow, false, MW);
}
// zoom = [a, b] (sample indices) or null; drag across the plot to set it, double-click or "reset" to clear
let modalPlot = null, modalX = null, cursor = null, zoom = null, drag = null;
function drawModal(x, hoverI = null, sel = null) {
  modalX = x;
  const cv = $("#m-canvas"), [a, b] = zoom || [0, x.length - 1];
  modalPlot = trace(cv, x.slice(a, b + 1), { color: cink(cv), pad: 8, lw: 1.2 });
  const { g, W, H, Y } = modalPlot, X = i => modalPlot.X(i - a);
  if (MW.on && MW.glow) {  // glow worm: the series stays dark; only the worm's trail lights it
    g.clearRect(0, 0, W, H);
    $("#m-readout").innerHTML = MW.journey ? `t = ${a}–${b}` : "only the glow worm's trail lights the series";
    return;
  }
  g.strokeStyle = css("--line"); g.lineWidth = 1; g.beginPath(); g.moveTo(0, H - .5); g.lineTo(W, H - .5); g.stroke();
  if (sel) { g.fillStyle = cink(cv); g.globalAlpha = .13; g.fillRect(Math.min(sel[0], sel[1]), 0, Math.abs(sel[1] - sel[0]), H); g.globalAlpha = 1; }
  const mark = (i, col) => { g.strokeStyle = col; g.lineWidth = 1.5; g.beginPath(); g.moveTo(X(i), 0); g.lineTo(X(i), H); g.stroke(); };
  if (cursor != null && cursor >= a && cursor <= b) mark(cursor, css("--ink"));
  const span = zoom ? (MW.on && MW.journey ? `t = ${a}–${b}, following the worm` : `t = ${a}–${b} · <button class="rz" type="button">reset zoom</button>`) : "";
  if (hoverI != null) {
    mark(hoverI, css("--ink-3"));
    g.fillStyle = cink(cv); g.strokeStyle = css("--surface"); g.lineWidth = 2;
    g.beginPath(); g.arc(X(hoverI), Y(x[hoverI]), 4, 0, 7); g.fill(); g.stroke();
    $("#m-readout").innerHTML = `t = ${hoverI} &nbsp; x = ${esc(fmt(x[hoverI]))}${zoom ? " · " + span.split(" · ")[1] : ""}`;
  } else $("#m-readout").innerHTML = zoom ? span : `${x.length} samples · drag to zoom`;
}
function modalIndexAt(px) {
  const [a, b] = zoom || [0, modalX.length - 1], r = $("#m-canvas").getBoundingClientRect();
  return Math.max(a, Math.min(b, a + Math.round(px / r.width * (b - a))));
}
function modalStep(d) {
  const k = modalList.indexOf(modalId);
  if (k >= 0) openSeries(modalList[(k + d + modalList.length) % modalList.length]);
}
function closeModal() {
  Audio.stop(); cursor = null; mwStop();
  const dlg = $("#modal"); if (dlg.open) dlg.close();
  modalId = null; discoSync();
  const h = location.hash, m = h.match(/^#\/(class\/[A-Z]+|map)\/.+/);
  if (m) {
    try { history.replaceState(null, "", `#/${m[1]}`); } catch {}
    // a neighbour jump may have crossed into another class: show that class's page underneath
    if (m[1].startsWith("class/") && toCode(m[1].slice(6)) !== $("#view").dataset.cls) route();
  }
}
function wireModal() {
  const dlg = $("#modal");
  $("#m-close").onclick = closeModal;
  $("#m-worm").onclick = () => MW.on ? mwStop() : mwStart();
  $("#m-glow").onclick = () => { MW.glow = !MW.glow; mwSync(); };
  $("#m-prev").onclick = () => modalStep(-1);
  $("#m-next").onclick = () => modalStep(1);
  dlg.addEventListener("close", () => { if (modalId) closeModal(); });
  dlg.addEventListener("click", e => { if (e.target === dlg) closeModal(); });
  dlg.addEventListener("keydown", e => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === "ArrowLeft") modalStep(-1);
    if (e.key === "ArrowRight") modalStep(1);
    if (e.key === " ") { e.preventDefault(); dlg.querySelector(".play.default").click(); }
  });
  const cv = $("#m-canvas"), px = e => e.clientX - cv.getBoundingClientRect().left;
  cv.addEventListener("mousedown", e => { if (modalX && !(MW.on && MW.journey)) { drag = { x0: px(e), x1: px(e) }; e.preventDefault(); } });
  cv.addEventListener("mousemove", e => {
    if (!modalX) return;
    if (drag) { drag.x1 = px(e); return drawModal(modalX, null, [drag.x0, drag.x1]); }
    drawModal(modalX, modalIndexAt(px(e)));
  });
  addEventListener("mouseup", () => {
    if (!drag || !modalX) return;
    const d = drag; drag = null;
    if (Math.abs(d.x1 - d.x0) > 6) {
      const i0 = modalIndexAt(Math.min(d.x0, d.x1)), i1 = modalIndexAt(Math.max(d.x0, d.x1));
      if (i1 - i0 >= 10) zoom = [i0, i1];
    }
    drawModal(modalX);
  });
  cv.addEventListener("dblclick", () => { zoom = null; if (modalX) drawModal(modalX); });
  $("#m-readout").addEventListener("click", e => { if (e.target.closest(".rz")) { zoom = null; drawModal(modalX); } });
  cv.addEventListener("mouseleave", () => modalX && !drag && drawModal(modalX));
  dlg.querySelectorAll(".play").forEach(b => b.onclick = () => {
    if (b.classList.contains("on")) return Audio.stop();
    const r = S.byId.get(modalId), x = modalX; if (!x) return;
    dlg.querySelectorAll(".play").forEach(o => o.classList.remove("on"));
    b.classList.add("on");
    const [a, z] = zoom || [0, x.length - 1];  // play only the zoomed window
    Audio.play(x.slice(a, z + 1), r, b.dataset.mode, {
      onpos: p => { cursor = a + p; drawModal(x); },
      done: () => { b.classList.remove("on"); cursor = null; if (modalX === x) drawModal(x); },
    });
  });
  const csv = () => "t,x\n" + modalX.map((v, i) => `${i},${v}`).join("\n") + "\n";
  $("#m-copy").onclick = e => {
    if (!modalX) return;
    const b = e.currentTarget, done = t => { b.textContent = t; setTimeout(() => { b.textContent = "Copy CSV"; }, 1500); };
    navigator.clipboard.writeText(csv()).then(() => done("Copied"), () => done("Copy failed"));
  };
  $("#m-csv").onclick = () => {
    if (!modalX) return;
    const blob = new Blob([csv()], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `${modalId}.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
}

// ---------- embedding map ----------
const mapState = { cls: "", tag: "", kind: "tsne", pin: null, hover: null };
const emb = () => S.embed[mapState.kind];
const varOf = (c, v) => { const el = document.createElement("i"); el.className = `k-${c}`; document.body.appendChild(el); const x = getComputedStyle(el).getPropertyValue(v).trim(); el.remove(); return x; };
async function viewMap(openId) {
  setNav("map");
  $("#view").dataset.cls = "";
  S.embed = S.embed || await getJSON("data/embed.json");
  const E = S.embed;
  const how = () => mapState.kind === "umap"
    ? `Each point is a series, placed by UMAP on its ${esc(E.features || "catch22")} features${E.n_features ? ` (${E.n_features.toLocaleString()})` : ""}. UMAP keeps somewhat more of the large-scale arrangement than t-SNE, and slightly less of the fine neighborhood structure.`
    : mapState.kind === "tsne"
    ? `Each point is a series, placed by t-SNE on its ${esc(E.features || "catch22")} features${E.n_features ? ` (${E.n_features.toLocaleString()})` : ""}, so series with similar dynamics sit together; distances between clusters are not meaningful.`
    : `Each point is a series, placed by the first two principal components of its ${esc(E.features || "catch22")} features${E.n_features ? ` (${E.n_features.toLocaleString()})` : ""} (${Math.round(E.explained[0] * 100)}% and ${Math.round(E.explained[1] * 100)}% of variance).`;
  $("#view").innerHTML = `
    <div class="maphead">
      <div><h1>Map of the corpus</h1><p><span id="mhow">${how()}</span> Move over the map to see the nearest series below; click to pin it.</p></div>
      <div class="mapctl">
        <span class="seg" role="group" aria-label="Embedding"><button data-k="tsne">t-SNE</button>${E.umap ? `<button data-k="umap">UMAP</button>` : ""}<button data-k="pca">PCA</button></span>
        <label>Highlight property <select id="mt"><option value="">none</option>${S.index.chip_tags.map(t => `<option value="${t}">${tagLabel(t)}</option>`).join("")}</select></label>
      </div>
    </div>
    <div class="mapwrap">
      <div class="legend" id="mlegend">${S.index.classes.map(c => `<button class="lg k-${c.code}" data-c="${c.code}" aria-pressed="false" title="${esc(c.title)}"><i></i>${c.short} <span>${esc(c.title)}</span></button>`).join("")}</div>
      <div class="legend groups" id="mgroups" hidden></div>
      <canvas id="mcv"></canvas>
    </div>
    <section class="mpanel" id="mpanel"></section>`;
  $("#mt").value = mapState.tag;
  $("#mt").onchange = e => { mapState.tag = e.target.value; if (mapState.tag) mapState.cls = ""; syncLegend(); drawMap(); };
  $("#mlegend").onclick = e => { const b = e.target.closest(".lg"); if (!b) return;
    mapState.cls = mapState.cls === b.dataset.c ? "" : b.dataset.c; if (mapState.cls) { mapState.tag = ""; $("#mt").value = ""; } syncLegend(); drawMap(); };
  const seg = () => document.querySelectorAll(".seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.k === mapState.kind));
  document.querySelectorAll(".seg button").forEach(b => b.onclick = () => { mapState.kind = b.dataset.k; seg(); $("#mhow").textContent = how(); drawMap(); });
  seg(); syncLegend();
  const cv = $("#mcv");
  cv.addEventListener("mousemove", e => { const id = mapHit(e); cv.style.cursor = "pointer";
    if (id !== mapState.hover) { mapState.hover = id; drawMap(); renderPanel(id || mapState.pin); } });
  cv.addEventListener("mouseleave", () => { mapState.hover = null; drawMap(); renderPanel(mapState.pin); });
  cv.addEventListener("click", e => { mapState.pin = mapHit(e); drawMap(); renderPanel(mapState.pin); });
  if (openId && S.byId.has(openId)) mapState.pin = openId;
  drawMap(); renderPanel(mapState.pin);
  if (openId) openSeries(openId, false);
}
// Within-class view: a focused class's points are coloured by process (at most 8 groups; the largest 7
// families plus "other", or by applied domain for NAT). Colours are the validated categorical palette.
const CAT = { light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
              dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"] };
const isDark = () => { const t = document.documentElement.dataset.theme; return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
function focusGroups(code) {
  const recs = S.meta.filter(r => r.cls === code);
  let key, names;
  if (code === "N") {
    key = r => r.tags.domain || "abstract";
    names = k => k;
  } else {
    const fam = S.cls.get(code).families;
    key = r => r.family;
    names = k => (fam.find(f => f.key === k) || {}).label || k;
  }
  const counts = {};
  for (const r of recs) counts[key(r)] = (counts[key(r)] || 0) + 1;
  let order = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);
  const other = order.length > 8 ? order.slice(7) : [];
  if (other.length) order = order.slice(0, 7).concat(["__other"]);
  const idx = Object.fromEntries(order.map((k, i) => [k, i]));
  other.forEach(k => { idx[k] = 7; });
  const groups = order.map(k => ({ name: k === "__other" ? `${other.length} other processes` : names(k),
                                   n: k === "__other" ? other.reduce((a, o) => a + counts[o], 0) : counts[k] }));
  return { of: r => idx[key(r)], groups };
}
function syncLegend() {
  document.querySelectorAll("#cbar .cp").forEach(p => p.toggleAttribute("aria-current", p.dataset.c === mapState.cls));
  document.querySelectorAll("#mlegend .lg").forEach(b => b.setAttribute("aria-pressed", b.dataset.c === mapState.cls));
  $("#mlegend").classList.toggle("focus", !!mapState.cls);
  const gl = $("#mgroups");
  if (!mapState.cls) { gl.hidden = true; return; }
  const pal = CAT[isDark() ? "dark" : "light"], G = focusGroups(mapState.cls);
  gl.hidden = false;
  gl.innerHTML = G.groups.map((g, i) => `<span class="grp"><i style="background:${pal[i]}"></i>${esc(g.name)} <b>${g.n}</b></span>`).join("");
}
let mapGeom = null;
function isHi(r) { return mapState.cls ? r.cls === mapState.cls : mapState.tag ? !!r.tags[mapState.tag] : true; }
function drawMap() {
  const cv = $("#mcv"); if (!cv) return;
  const [g, W, H] = fit(cv), E = emb();
  const pts = Object.values(E);
  let [x0, x1] = range(pts.map(p => p[0])), [y0, y1] = range(pts.map(p => p[1]));
  const m = 20, X = v => m + (v - x0) / (x1 - x0) * (W - 2 * m), Y = v => H - m - (v - y0) / (y1 - y0) * (H - 2 * m);
  mapGeom = { X, Y };
  if (mapState.kind === "pca") {
    g.strokeStyle = css("--line"); g.lineWidth = 1;
    g.beginPath(); g.moveTo(X(0), m / 2); g.lineTo(X(0), H - m / 2); g.moveTo(m / 2, Y(0)); g.lineTo(W - m / 2, Y(0)); g.stroke();
    g.fillStyle = css("--ink-3"); g.font = "11px Inter, sans-serif";
    g.fillText("PC1", W - m - 12, Y(0) - 6); g.fillText("PC2", X(0) + 6, m);
  }
  // class dots: the site's pastel as fill with a thin ring in the class's darker shade (as badges and cards)
  const col = {}, edge = {}; for (const c of S.index.classes) { col[c.code] = varOf(c.code, "--csoft"); edge[c.code] = varOf(c.code, "--cink"); }
  const surf = css("--surface");
  const dot = (p, r, fill, a, edge = surf, w = 1) => { g.globalAlpha = a; g.beginPath(); g.arc(X(p[0]), Y(p[1]), r, 0, 7); g.fillStyle = fill; g.fill(); g.lineWidth = w; g.strokeStyle = edge; g.stroke(); };
  const hi = [], lo = [];
  for (const [id, p] of Object.entries(E)) (isHi(S.byId.get(id)) ? hi : lo).push([id, p]);
  const G = mapState.cls ? focusGroups(mapState.cls) : null, pal = CAT[isDark() ? "dark" : "light"];
  const fill = r => G ? pal[G.of(r)] : col[r.cls];
  for (const [id, p] of lo) { const k = S.byId.get(id).cls; G ? dot(p, 3.4, css("--context"), .5) : dot(p, 3.6, col[k], .2, edge[k], .8); }
  for (const [id, p] of hi) { const k = S.byId.get(id).cls; G ? dot(p, 4.5, fill(S.byId.get(id)), 1) : dot(p, 4.4, col[k], 1, edge[k], 1.1); }
  g.globalAlpha = 1;
  const ring = (id, r, w) => { const p = E[id]; if (!p) return; g.beginPath(); g.arc(X(p[0]), Y(p[1]), r, 0, 7); g.lineWidth = w; g.strokeStyle = css("--ink"); g.stroke(); };
  if (mapState.pin) ring(mapState.pin, 8, 2);
  if (mapState.hover && mapState.hover !== mapState.pin) ring(mapState.hover, 7, 1.25);
}
// Snap to the nearest series anywhere on the map (among the highlighted ones when a class or property is highlighted).
function mapHit(e) {
  if (!mapGeom) return null;
  const r = $("#mcv").getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const only = mapState.cls || mapState.tag;
  let best = null, bd = Infinity;
  for (const [id, p] of Object.entries(emb())) {
    if (only && !isHi(S.byId.get(id))) continue;
    const d = (mapGeom.X(p[0]) - mx) ** 2 + (mapGeom.Y(p[1]) - my) ** 2;
    if (d < bd) { bd = d; best = id; }
  }
  return best;
}
async function renderPanel(id, force = false) {
  const el = $("#mpanel"); if (!el) return;
  if (!force && el.dataset.id === (id || "")) return;
  el.dataset.id = id || "";
  if (!id) { el.className = "mpanel empty"; el.innerHTML = `<p>Hover over a point to see its series here.</p>`; return; }
  const r = S.byId.get(id), c = S.cls.get(r.cls), f = S.fam.get(`${r.cls}.${r.family}`);
  const tags = Object.entries(r.tags).filter(([k]) => k !== "stationary" && k !== "domain");
  const nums = Object.entries(r.nums).slice(0, 4);
  el.className = `mpanel k-${r.cls}`;
  el.innerHTML = `
    <div class="mp-head">
      <span class="letter">${sc(r.cls)}</span>
      <div class="mp-title"><b>${esc(r.name)}</b> <span class="mono">${r.id}</span>
        <div>${esc(c.title)} <span class="lbls">${labelTags(r)}</span></div></div>
      <button class="play" id="mp-play"><span class="tri"></span>Listen</button>
      <button class="ghost" id="mp-open">Open details</button>
    </div>
    <canvas class="mp-trace"></canvas>
    <div class="mp-info">
      <p>${esc(f.card.description)}</p>
      <div>
        <div class="tags">${tags.map(([k, v]) => `<span class="tag ${v === "partly" ? "partly" : ""}"${TAG_TIP[k] ? ` title="${esc(TAG_TIP[k])}"` : ""}>${tagLabel(k)}</span>`).join("")}<span class="tag">${esc(r.tags.domain || "abstract")}</span></div>
        ${nums.length ? `<div class="mp-nums">${nums.map(([k, v]) => `<span>${NUM_LABEL[k] || k} <b>${fmt(v)}</b></span>`).join("")}</div>` : ""}
      </div>
    </div>`;
  mathify(el);
  $("#mp-open").onclick = () => openSeries(id);
  const x = await seriesOf(id);
  if (el.dataset.id !== id) return;
  trace($(".mp-trace", el), x, { color: cink(el), lw: 1.1 });
  const pb = $("#mp-play");
  pb.onclick = () => { if (pb.classList.contains("on")) return Audio.stop();
    pb.classList.add("on"); Audio.play(x, r, Audio.defaultMode(r), { done: () => pb.classList.remove("on") }); };
}

// ---------- data / about ----------
function viewAbout() {
  setNav("about"); $("#view").dataset.cls = "";
  const I = S.index, v = I.versions;
  $("#view").innerHTML = `<div class="prose">
    <h1>Data and reproducibility</h1>
    <p>This release is the stationary stage of the collection: ${I.n} series of ${I.T} samples, all passing a five-window mean and variance stationarity gate, with a real-valued, finite-variance marginal. A second, non-stationary stage will follow.</p>
    <h2>Downloads</h2>
    <p>All files are on figshare (CC BY 4.0): <a href="https://doi.org/10.6084/m9.figshare.34013331" target="_blank" rel="noopener">doi:10.6084/m9.figshare.34013331</a>. Any single series can also be downloaded as CSV from its pop-up.</p>
    <div class="dl">
      <div><b>metadata.csv</b>one row per series: process, seed, property tags, ground truth, drawn parameters</div>
      <div><b>series.npz</b>NumPy: the 1000 × 1000 array and the series IDs</div>
      <div><b>${esc(I.inp)}</b>hctsa input file (series, IDs, keywords)</div>
      <div><b>HCTSA_1000x1000.mat</b>full hctsa feature matrix: 1000 series × 7077 features</div>
      <div><b>hctsa_*.csv</b>the series and the feature matrix as CSV</div>
      <div><b>README.md</b>file formats, columns and tags</div>
    </div>
    <h2>How to cite</h2>
    <p class="cite">Fulcher, B. D. (2026). The 1000×1000 collection: 1000 synthetic time series from 133 dynamical processes. figshare. Dataset. <a href="https://doi.org/10.6084/m9.figshare.34013331" target="_blank" rel="noopener">https://doi.org/10.6084/m9.figshare.34013331</a></p>
    <p>If you use the hctsa features, please also cite B. D. Fulcher and N. S. Jones, <i>Cell Systems</i> 5, 527 (2017), <a href="https://doi.org/10.1016/j.cels.2017.10.001" target="_blank" rel="noopener">doi:10.1016/j.cels.2017.10.001</a>.</p>
    <h2>Series IDs</h2>
    <p>Series IDs use the collection's short code, <b>S1000</b>: <code>S1000_&lt;class&gt;_&lt;family&gt;_&lt;index&gt;</code>, e.g. <code>S1000_FLOW_dysts-flow_020</code> (the Chua circuit). The class is its code as used throughout this site (e.g. FLOW for chaotic flows), and the index counts the instances of a family from 000.</p>
    <h2>Regenerate</h2>
    <p>Every series is generated from its own named random stream (recorded as <code>seed_name</code> in the metadata), so any one of them can be rebuilt on its own and checked against its hash.${REPO_PUBLIC ? ` The code is at <a href="${REPO}">${REPO.replace("https://", "")}</a>.` : " The generator code will be made public soon."}</p>
    <pre class="cli">pip install -e .
s1000 build --profile ${I.release} --export
s1000 verify --profile ${I.release} --fraction 0.25 --cold</pre>
    <h2>Build</h2>
    <p>Built ${esc(I.built)} with Python ${esc(v.python)}, NumPy ${esc(v.numpy)}, SciPy ${esc(v.scipy)}.</p>
    <h2>Listening</h2>
    <p><b>Waveform</b> plays the series as sound, resampled so its dominant period sits at 220 Hz: chaotic flows buzz with timbre, narrowband noise wobbles in pitch, intermittency crackles. <b>Pitch contour</b> maps the value to the pitch of a sine over two octaves, the 1000 samples lasting 4 s, which suits slow, bursty or regime-switching series. Each series has a default; press space in a series view to play it.</p>
  </div>`;
}

// ---------- quiz: which process made this series? ----------
// Ten rounds, one series from each of ten classes (M, the observation transforms, is left out: its cards describe
// the transform, not the dynamics you see). Easy distractors come from other classes, far away in feature space;
// hard ones are the series' nearest look-alikes from other families (data/quiz.json). A round is seeded by the
// date, so everyone gets the same "today's round"; "random round" draws a fresh seed.
const QN = 10;
const Q = { mode: "match", diff: "easy", seed: "", rounds: [], i: 0, picks: [], playing: null, view: "phase", zooms: {}, wormAt: 0, sview: "global", glow: false };  // sview: global / journey framing; glow: the dark glow-worm lighting (either framing)
const QDIFF = { easy: "Normal", hard: "Devil mode 😈" };  // display names; "easy"/"hard" stay the internal keys (seeds, stored bests)
const QMODES = { match: ["Match", "See a series, pick the process that made it."],
  reverse: ["Reverse", "Read a process, pick the series it made."],
  listen: ["Listen", "Hear a series (no peeking), pick the process that made it."] };
const store = { get(k, d) { try { const v = localStorage.getItem("s1000q." + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("s1000q." + k, JSON.stringify(v)); } catch {} } };
const qToday = () => new Date().toLocaleDateString("en-CA");  // YYYY-MM-DD, local
function qrng(str) {  // string-seeded PRNG (cyrb-style hash into mulberry32)
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) { h = Math.imul(h ^ str.charCodeAt(i), 3432918353); h = h << 13 | h >>> 19; }
  let a = h >>> 0;
  return () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
const qgroup = r => r.family.startsWith("dysts") ? "dysts" : `${r.cls}.${r.family}`;  // dysts families share their systems
const qlook = id => (S.quiz.look[S.quiz.row.get(id)] || []).map(([j, d]) => [S.quiz.ids[j], d]);
const qdist = (a, b) => { const x = qlook(a).find(([j]) => j === b) || qlook(b).find(([j]) => j === a); return x ? x[1] : null; };

function quizDeal(seed) {
  const rnd = qrng(`${seed}|${Q.mode}|${Q.diff}`), pick = a => a[Math.floor(rnd() * a.length)];
  const shuf = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const pool = S.meta.filter(r => r.cls !== "M");
  const classes = shuf([...new Set(pool.map(r => r.cls))].sort()).slice(0, QN);
  return classes.map(c => {
    const r = pick(pool.filter(m => m.cls === c)), out = [], groups = new Set([qgroup(r)]), names = new Set([r.name]);
    const ok = m => m && m.cls !== "M" && !groups.has(qgroup(m)) && !names.has(m.name);
    const take = m => { out.push(m.id); groups.add(qgroup(m)); names.add(m.name); };
    const near = qlook(r.id);
    if (Q.diff === "hard") for (const m of shuf(near.map(([j]) => S.byId.get(j)).filter(ok).slice(0, 5))) if (out.length < 2 && ok(m)) take(m);
    const nearSet = new Set(near.map(([j]) => j));
    for (let n = 0; out.length < 2 && n < 5000; n++) {
      const m = pick(pool);
      if (ok(m) && m.cls !== r.cls && !nearSet.has(m.id) && !out.some(o => S.byId.get(o).cls === m.cls)) take(m);
    }
    return { id: r.id, opts: shuf([r.id, ...out]) };
  });
}
// ---------- quiz sounds: a synthesized call for each class mascot ----------
// Right answer: the answer's mascot calls, then a rising two-note chime. Wrong: always the same falling "womp", so
// a mascot's call means you caught it. Everything is synthesized (oscillators, filtered noise), so there are no audio files to load.
function sTone(ctx, dest, { type = "sine", f0, f1 = f0, t, dur, v = .3, a = .01, lin = false, filter = null, vib = null, am = null }) {
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = type; o.frequency.setValueAtTime(f0, t);
  if (f1 !== f0) o.frequency[lin ? "linearRampToValueAtTime" : "exponentialRampToValueAtTime"](f1, t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + a); g.gain.exponentialRampToValueAtTime(.001, t + dur);
  let node = o;
  if (filter) { const fl = ctx.createBiquadFilter(); fl.type = filter[0]; fl.frequency.value = filter[1]; fl.Q.value = filter[2] || 1; node.connect(fl); node = fl; }
  if (vib) sLfo(ctx, o.frequency, vib[0], vib[1], t, dur);
  if (am) { const m = ctx.createGain(); m.gain.value = .5; sLfo(ctx, m.gain, am, .5, t, dur); node.connect(m); node = m; }
  node.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + .05);
}
function sLfo(ctx, param, rate, depth, t, dur) {
  const l = ctx.createOscillator(), g = ctx.createGain(); l.frequency.value = rate; g.gain.value = depth;
  l.connect(g); g.connect(param); l.start(t); l.stop(t + dur + .05);
}
function sNoise(ctx, dest, { t, dur, v = .3, type = "bandpass", f = 1000, f1 = f, q = 1, a = .004, am = null }) {
  const n = Math.ceil(ctx.sampleRate * (dur + .05)), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  const s = ctx.createBufferSource(), fl = ctx.createBiquadFilter(), g = ctx.createGain();
  s.buffer = b; fl.type = type; fl.Q.value = q; fl.frequency.setValueAtTime(f, t);
  if (f1 !== f) fl.frequency.exponentialRampToValueAtTime(f1, t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + a); g.gain.exponentialRampToValueAtTime(.001, t + dur);
  let node = fl; s.connect(fl);
  if (am) { const m = ctx.createGain(); m.gain.value = .5; sLfo(ctx, m.gain, am, .5, t, dur); fl.connect(m); node = m; }
  node.connect(g); g.connect(dest); s.start(t); s.stop(t + dur + .05);
}
// each voice schedules from t with pitch factor p and returns its length in seconds
const VOICES = {
  goldfish(c, o, t, p) { [0, .12, .22].forEach((d, i) => sTone(c, o, { f0: 320 * p * (1 + .15 * i), f1: 1100 * p * (1 + .15 * i), t: t + d, dur: .08, v: .35 })); return .35; },
  jellyfish(c, o, t, p) { sTone(c, o, { f0: 540 * p, f1: 330 * p, t, dur: .95, v: .28, a: .12, lin: true, vib: [5, 16] });
    sTone(c, o, { type: "triangle", f0: 1080 * p, f1: 660 * p, t, dur: .9, v: .06, a: .15, lin: true }); return .95; },
  stingray(c, o, t, p) { sNoise(c, o, { t, dur: .6, v: .55, f: 350 * p, f1: 2600 * p, q: 3 }); sNoise(c, o, { t: t + .25, dur: .45, v: .3, type: "lowpass", f: 900 * p, f1: 250 * p }); return .7; },
  elephant(c, o, t, p) { sTone(c, o, { type: "sawtooth", f0: 250 * p, f1: 560 * p, t, dur: .3, v: .3, a: .04, filter: ["bandpass", 1000, 1.5], vib: [7, 14] });
    sTone(c, o, { type: "sawtooth", f0: 560 * p, f1: 380 * p, t: t + .28, dur: .45, v: .28, a: .02, filter: ["bandpass", 1000, 1.5], vib: [7, 14] }); return .75; },
  chameleon(c, o, t, p) { sTone(c, o, { f0: 2400 * p, f1: 170 * p, t, dur: .1, v: .4, a: .003 }); sNoise(c, o, { t: t + .13, dur: .03, v: .4, type: "highpass", f: 3000 });
    sTone(c, o, { f0: 190 * p, f1: 120 * p, t: t + .2, dur: .14, v: .3 }); return .36; },
  frog(c, o, t, p) { [[0, 110], [.22, 128]].forEach(([d, f]) => sTone(c, o, { type: "square", f0: f * p, f1: f * p * .92, t: t + d, dur: .17, v: .35, a: .005, filter: ["bandpass", 750, 4], am: 30 })); return .42; },
  butterfly(c, o, t, p) { sNoise(c, o, { t, dur: .5, v: .22, type: "highpass", f: 2500, am: 17 });
    [1568, 2093].forEach((f, i) => sTone(c, o, { f0: f * p, t: t + .1 + i * .16, dur: .25, v: .12, a: .004 })); return .55; },
  firefly(c, o, t, p) { [1047, 1319, 1568, 2093].forEach((f, i) => sTone(c, o, { f0: f * p, t: t + i * .09, dur: .5, v: .16, a: .003 })); return .8; },
  bee(c, o, t, p) { sTone(c, o, { type: "sawtooth", f0: 190 * p, f1: 225 * p, t, dur: .8, v: .22, a: .05, lin: true, filter: ["lowpass", 1400, 1], vib: [9, 12] }); return .8; },
  woodpecker(c, o, t, p) { [0, .055, .11, .165, .22, .45, .505, .56].forEach(d => sNoise(c, o, { t: t + d, dur: .035, v: .55, f: 1800 * p, q: 6, a: .001 })); return .62; },
  octopus(c, o, t, p) { [[0, 230], [.2, 270], [.42, 190]].forEach(([d, f]) => sTone(c, o, { f0: f * p, f1: f * p / 2, t: t + d, dur: .18, v: .38, a: .01, filter: ["lowpass", 900, 2] })); return .62; },
  owl(c, o, t, p) { [[0, 392, .38], [.48, 330, .22], [.74, 330, .32]].forEach(([d, f, l]) => sTone(c, o, { f0: f * p, f1: f * p * .97, t: t + d, dur: l, v: .3, a: .07 }));
    sNoise(c, o, { t, dur: .3, v: .04, type: "lowpass", f: 700 }); return 1.08; },
  beaver(c, o, t, p) { sNoise(c, o, { t, dur: .14, v: .7, type: "lowpass", f: 700 * p, q: 1, a: .001 });
    [.26, .34, .42].forEach(d => sNoise(c, o, { t: t + d, dur: .045, v: .45, f: 2600 * p, q: 3, a: .001 })); return .5; },
};
const Sfx = {
  on: store.get("sound", true),
  play(name, ok, { chime = true } = {}) {
    if (!this.on) return;
    let c; try { c = Audio.ctx = Audio.ctx || new (window.AudioContext || window.webkitAudioContext)(); } catch { return; }
    if (c.state === "suspended") c.resume();
    const out = c.createGain(), t = c.currentTime + .03; out.gain.value = .55; out.connect(c.destination);
    if (!ok) { sTone(c, out, { type: "triangle", f0: 330, f1: 200, t, dur: .3, v: .22 }); sTone(c, out, { type: "triangle", f0: 247, f1: 140, t: t + .26, dur: .45, v: .22 }); return; }
    const len = (VOICES[name] || VOICES.goldfish)(c, out, t, 1);
    if (!chime) return;
    const u = t + len + .06;
    sTone(c, out, { f0: 880, t: u, dur: .22, v: .16 }); sTone(c, out, { f0: 1318.5, t: u + .1, dur: .4, v: .16 });
  },
};
// ---------- glow-worm disco: a synthesized disco loop and a spinning mirror ball while the glow worm is out ----------
// It hangs in the top-right corner of the dark box the glow worm crawls in. On whenever a glow worm is crawling (the quiz's glow worm, or the pop-up's Worm + Glow worm). The loop is scheduled
// a little ahead of the audio clock (118 bpm, 16th-note steps): four-on-the-floor kick, off-beat open hats, claps on
// 2 and 4, an octave-bouncing bass and chord stabs over an Am9 | Am9 | D9 | D9 vamp, with a string pad and, every
// other time round, a pentatonic sparkle. Clicking the ball mutes or unmutes the music (remembered); the quiz's
// Sound off silences it too.
const DSTEP = 60 / 118 / 4, DNOTE = m => 440 * 2 ** ((m - 69) / 12);
const DCHORDS = [[45, [60, 64, 67, 71]], [45, [60, 64, 67, 71]], [50, [66, 69, 72, 76]], [50, [66, 69, 72, 76]]];
const DARP = [69, 72, 74, 76, 79, 81, 79, 76];
const Disco = {
  music: store.get("disco", true), ctx: null, out: null, timer: 0, next: 0, step: 0, raf: 0, el: null, noise: null, host: null,
  hit(t, dur, v, type, f, q = 1) {  // a burst of the shared noise buffer through one filter
    const c = this.ctx, s = c.createBufferSource(), fl = c.createBiquadFilter(), g = c.createGain();
    s.buffer = this.noise; fl.type = type; fl.frequency.value = f; fl.Q.value = q;
    g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.001, t + dur);
    s.connect(fl); fl.connect(g); g.connect(this.out); s.start(t, Math.random() * 1.5); s.stop(t + dur + .02);
  },
  beat(k, t) {
    const c = this.ctx, o = this.out, s = k % 16, bar = (k >> 4) % 4, [root, chord] = DCHORDS[bar], lap = (k >> 6) % 2;
    if (s % 4 === 0) { sTone(c, o, { f0: 150, f1: 42, t, dur: .3, v: .9, a: .002 }); this.hit(t, .012, .3, "highpass", 3000); }
    if (s % 4 === 2) this.hit(t, .11, .16, "highpass", 7500);
    else this.hit(t, .03, .05, "highpass", 9000);
    if (s === 4 || s === 12) { [0, .011, .022].forEach(d => this.hit(t + d, .02, .45, "bandpass", 1400, 1.2)); this.hit(t + .03, .16, .3, "bandpass", 1300, 1); }
    if (s % 2 === 0) {  // bass: root and its octave, a slide up to the 7th at the end of the bar
      const m = s === 14 ? root + 10 : root + (s % 4 ? 12 : 0);
      sTone(c, o, { type: "sawtooth", f0: DNOTE(m), t, dur: .16, v: .32, a: .005, filter: ["lowpass", 650, 5] });
    }
    if (s === 6 || s === 10 || s === 14) chord.forEach(m => sTone(c, o, { type: "sawtooth", f0: DNOTE(m), t, dur: .16, v: .045, a: .004, filter: ["lowpass", 2600, 1] }));
    if (s === 0 && bar % 2 === 0) chord.forEach(m => sTone(c, o, { type: "sawtooth", f0: DNOTE(m + 12), t, dur: 32 * DSTEP, v: .018, a: .5, filter: ["lowpass", 1800, .7], vib: [5, 3] }));
    if (lap && s % 2 === 1) sTone(c, o, { type: "square", f0: DNOTE(DARP[(s >> 1) % 8] + (bar >= 2 ? 5 : 0)), t, dur: .09, v: .035, a: .003, filter: ["lowpass", 3200, 1] });
  },
  start() {
    if (this.timer) return;
    let c; try { c = this.ctx = Audio.ctx = Audio.ctx || new (window.AudioContext || window.webkitAudioContext)(); } catch { return; }
    if (c.state === "suspended") c.resume();
    if (!this.noise) { const n = c.sampleRate * 2, b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0); for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1; this.noise = b; }
    this.out = c.createGain(); this.out.gain.setValueAtTime(0, c.currentTime); this.out.gain.linearRampToValueAtTime(.2, c.currentTime + .6); this.out.connect(c.destination);
    this.next = c.currentTime + .08; this.step = 0;
    this.timer = setInterval(() => {
      if (!discoWhere() || !this.el || !this.el.isConnected) return discoSync();
      const now = c.currentTime;
      if (this.next < now - .05) this.next = now + .05;  // a throttled (background) tab: skip ahead rather than burst
      while (this.next < now + .15) { this.beat(this.step++, this.next); this.next += DSTEP; }
    }, 30);
  },
  stop() {
    if (!this.timer) return;
    clearInterval(this.timer); this.timer = 0;
    const o = this.out, t = this.ctx.currentTime; o.gain.cancelScheduledValues(t); o.gain.setValueAtTime(o.gain.value, t); o.gain.linearRampToValueAtTime(0, t + .25);
    setTimeout(() => o.disconnect(), 400);
  },
  ball() {
    if (this.el) return this.el;
    const b = this.el = document.createElement("button");
    b.type = "button"; b.className = "disco";
    b.innerHTML = `<span class="disco-cord"></span><canvas></canvas><span class="disco-note" aria-hidden="true">♪</span>`;
    b.onclick = () => { this.music = !this.music; store.set("disco", this.music); discoSync(); };
    return b;
  },
  draw(t) {  // an 8-bit mirror ball: a 20 x 20 pixel sprite, a five-grey palette and pixel glints, turning at 8 frames a second
    const cv = this.el.querySelector("canvas"), N = 20;
    if (cv.width !== N) cv.width = cv.height = N;
    const g = cv.getContext("2d"), img = g.createImageData(N, N), d = img.data, f = Math.floor(t / 125);
    const GREY = ["#2a2d3a", "#4b5063", "#7c8298", "#b3b8cc", "#e8ebf5"], GLINT = ["#ff5fd2", "#5ff3ff", "#fff35f", "#8dff6e"];
    const rgb = h => [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16));
    const put = (x, y, h) => { if (x < 0 || y < 0 || x >= N || y >= N) return; const [r, gg, b] = rgb(h), k = 4 * (y * N + x); d[k] = r; d[k + 1] = gg; d[k + 2] = b; d[k + 3] = 255; };
    const c = 9.5, R = 8;
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      const dx = x - c, dy = y - c, rr = Math.hypot(dx, dy);
      if (rr > R) continue;
      if (rr > R - 1) { put(x, y, "#1a1c26"); continue; }  // outline
      const w = Math.sqrt(R * R - dy * dy), lon = Math.asin(Math.max(-1, Math.min(1, dx / w)));
      const col = Math.floor(lon / Math.PI * 8 + f / 2), row = Math.floor((dy + R) / 2.2);
      const lit = Math.max(0, Math.min(4, Math.round(2.6 - (dx + dy) / 3.6 + ((col + row) & 1 ? -.7 : .5))));
      const h = (col * 7 + row * 13) % 11;
      put(x, y, h === 0 && lit >= 2 ? GLINT[(row + col) & 3] : GREY[lit]);
    }
    const sp = [[2, 3], [17, 2], [1, 16], [18, 15]][f % 4], on = (f >> 2) & 1;  // a pixel sparkle hopping round the corners
    if (on) { const hc = GLINT[(f >> 3) & 3]; [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([a, b]) => put(sp[0] + a, sp[1] + b, hc)); }
    g.putImageData(img, 0, 0);
  },
};
// the ball shows whenever a glow worm is out; the music plays too unless muted (by the ball, or the quiz's Sound off)
// (and never in a hidden tab); the scheduler re-checks this every tick, so the music can't outlive the ball
function discoWhere() {
  if (document.hidden) return null;
  const dlg = $("#modal");
  if (dlg.open) return MW.on && MW.glow ? "modal" : null;
  return location.hash.startsWith("#/quiz") && document.querySelector(".qscope.glowing .qs-wrap") ? "quiz" : null;
}
function discoSync() {
  const where = discoWhere(), dlg = $("#modal"), inModal = where === "modal", on = !!where;
  if (!on) {
    Disco.stop();
    if (Disco.el) { Disco.el.remove(); cancelAnimationFrame(Disco.raf); Disco.raf = 0; }
    return;
  }
  const b = Disco.ball(), host = inModal ? $("#modal .m-plot") : document.querySelector(".qscope.glowing .qs-wrap");
  if (b.parentNode !== host) host.appendChild(b);
  const music = Disco.music && Sfx.on;
  b.classList.toggle("muted", !music);
  b.setAttribute("aria-pressed", music);
  b.setAttribute("aria-label", music ? "Disco music on: click to mute" : "Disco music off: click to play");
  b.title = music ? "Mute the disco" : "Play the disco";
  music ? Disco.start() : Disco.stop();
  if (!Disco.raf) {
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const loop = now => { if (!Disco.el || !Disco.el.isConnected) { Disco.raf = 0; return; } Disco.draw(still ? 0 : now); Disco.raf = requestAnimationFrame(loop); };
    Disco.draw(0); Disco.raf = requestAnimationFrame(loop);
  }
}
document.addEventListener("visibilitychange", () => discoSync());
function quizStart(seed) { Audio.stop(); Q.playing = null; Q.seed = seed; Q.rounds = quizDeal(seed); Q.i = 0; Q.picks = []; Q.saved = false; Q.zooms = {}; Q.wormAt = 0; }

async function viewQuiz() {
  setNav("quiz"); $("#view").dataset.cls = "";
  if (!S.quiz) { S.quiz = await getJSON("data/quiz.json"); S.quiz.row = new Map(S.quiz.ids.map((id, i) => [id, i])); }
  if (!Q.rounds.length) quizStart(qToday());
  quizRender();
}

const qfirst = t => {
  const m = String(t).match(/^[\s\S]*?[.!?](?=\s+[A-Z]|\s*$)/); let s = m ? m[0] : String(t);
  if (s.length > 190) {
    let cut = s.lastIndexOf(" ", 180);
    const open = s.lastIndexOf("\\(", cut), close = s.lastIndexOf("\\)", cut);
    if (open > close) cut = s.lastIndexOf(" ", open);
    s = s.slice(0, cut).replace(/[,;:(]+$/, "") + "…";
  }
  return s;
};
// card equations: a long single line breaks into stacked lines, then shrinks to fit
// split TeX at top-level gaps (\qquad, \quad, ",\ \ ") outside any {...} or \left...\right, keeping the pieces' order
function qsplit(t) {
  const out = []; let depth = 0, cur = "";
  for (let i = 0; i < t.length;) {
    const rest = t.slice(i), gap = depth === 0 && (rest.match(/^\\qquad(?![a-zA-Z])/) || rest.match(/^\\quad(?![a-zA-Z])/) || rest.match(/^,\\ \\ /));
    if (gap) { cur = (gap[0][0] === "," ? cur + "," : cur).trim(); if (cur) out.push(cur); cur = ""; i += gap[0].length; continue; }
    const lr = rest.match(/^\\(left|right)(?![a-zA-Z])/);
    if (lr) { depth += lr[1] === "left" ? 1 : -1; cur += lr[0]; i += lr[0].length; continue; }
    const c = t[i];
    if (c === "\\" && i + 1 < t.length) { cur += c + t[i + 1]; i += 2; continue; }
    if (c === "{") depth++; else if (c === "}") depth--;
    cur += c; i++;
  }
  if (cur.trim()) out.push(cur.trim());
  // a leading label ("\text{Izhikevich: } ...") gets its own line
  const m = out[0] && out[0].match(/^(\\text\{[^{}]*:\s*\})\s*(.+)$/);
  if (m) out.splice(0, 1, m[1], m[2]);
  return out;
}
// "or" between alternatives starts its own line: "a \quad\text{or}\quad b" -> "a", "\text{or } b"
const qtex = t => {
  if (/\\begin/.test(t)) return t;
  const parts = qsplit(t.replace(/\s*\\quad\s*\\text\{\s*or\s*\}\s*\\quad\s*/g, " \\qquad \\text{or } "))
    .map(x => x.replace(/^\\text\{\s*or\s*\}\s*$/, "")).filter(Boolean);
  return parts.length > 1 ? `\\begin{gathered}${parts.join(" \\\\ ")}\\end{gathered}` : t;
};
// a variant's aligned lines split the same way; continuation pieces align on their own "="
function qalignLines(lines) {
  return lines.flatMap(l => { const [h, ...rest] = qsplit(l); return [h, ...rest.map(x => x.includes("&") ? x : x.replace(/=/, "&="))]; });
}
function qcardTex(r) {
  const card = S.fam.get(`${r.cls}.${r.family}`).card || {};
  return r.eqs ? `\\begin{aligned}${qalignLines(r.eqs.lines).join(" \\\\ ")}\\end{aligned}` : (card.equations || [])[0] ? qtex(card.equations[0]) : "";
}
function qfitEq(el) {
  let px = 13; el.style.fontSize = px + "px";
  while (el.scrollWidth > el.clientWidth + 1 && px > 10) el.style.fontSize = (px -= .5) + "px";
  if (el.scrollWidth <= el.clientWidth + 1 || !window.katex) return;
  // still too wide: one line per row, each in inline mode, which wraps at relations and binary operators like text
  const rows = el.dataset.tex.replace(/\\(begin|end)\{(aligned|gathered)\}/g, "").split(/\\\\/).map(x => x.replace(/&/g, "").trim()).filter(Boolean);
  el.innerHTML = rows.map(() => `<span class="qc-row"></span>`).join("");
  el.querySelectorAll(".qc-row").forEach((sp, i) => katex.render(`\\displaystyle ${rows[i]}`, sp, { displayMode: false, throwOnError: false }));
  el.classList.add("wrap");
}
// this series' parameter values: the variant's explicit equation parameters when it has them, else its drawn
// parameters, minus bookkeeping (which system, which coordinate, base series ids, ...)
const QSKIP = new Set(["kind", "system", "coord", "observed", "observation", "base_id", "base_family", "base_index", "which", "near", "one_sided", "seed", "hops"]);  // hops: an outcome count, not a parameter
const QGREEK = new Set(["alpha", "beta", "gamma", "delta", "epsilon", "kappa", "lambda", "mu", "nu", "rho", "sigma", "tau", "theta", "phi", "psi", "omega", "xi", "eta", "zeta", "Phi", "Theta", "Omega", "Lambda", "Sigma", "Delta", "Gamma"]);
const QNAMES = { gauss_sd: "\\text{Gaussian noise s.d.}", q_kernel: "h_{jk}", amplitudes: "a_k", transitions: "\\text{transition matrix (by row)}",
  storm_dur: "\\text{mean storm duration}", cell_dur: "\\text{mean cell duration}", mean_int: "\\text{mean cell intensity}", noise_sd: "\\text{noise s.d.}",
  w0tau: "\\omega_0\\tau", a_hf: "a_{\\mathrm{HF}}", smooth_bw: "\\text{smoothing bandwidth}", N0: "N_0",
  ppp: "\\text{samples per period}", eps: "\\epsilon", lam: "\\lambda", lam1: "\\lambda_1", lam2: "\\lambda_2", phis: "\\phi", lf_hf: "\\text{LF/HF}", period_time: "\\text{period (time)}",
  replay_fraction: "\\text{fraction replayed}", n_replays: "\\text{replays}", replay_noise: "\\text{replay noise s.d.}",
  slow_period: "\\text{slow period}", fast_period: "\\text{fast period}", f1: "f_1", f2: "f_2" };
// generator parameter names -> the family card's own notation (null: an outcome, not a parameter; hide it)
const QSYM = {
  "A.bimodal": { separation: "\\Delta", weight: "w" }, "A.exponential-pareto": { tail: "\\alpha" },
  "A.skewed": { sigma_log: "\\sigma", df: "k", shape: "k" },
  "B.ar2": { a: "\\phi", modulus: "r", pseudo_period: "P", roots: null }, "B.arma": { a: "\\phi" }, "B.arp": { a: "\\phi" },
  "B.lowhigh-pass": { fc: "f_c", order: "n" }, "B.narrowband": { fc: "f_0" }, "B.seasonal-arma": { season: "s" },
  "B.random-spectrum": { amp_sd: "\\text{amplitude s.d.}", ell: "\\text{GP length scale}" },
  "C.ar-skew": { a: "\\phi", shape: "k" }, "C.arma-heavy": { a: "\\phi" }, "C.levy-ou": { decay: "a", rate: "\\text{jump rate}" },
  "C.ma-asym-skew": { shape: "\\text{innovation shape}" }, "C.shot-noise": { rate: "\\lambda", width: "\\text{pulse width}" },
  "D.arfima": { ar: "\\phi", ma: "\\theta" }, "D.discrete-cascade": { pm: "p", lam: "\\lambda" }, "D.lmsv": { Hw: "H_w", sw: "s" },
  "D.mrw": { lam2: "\\lambda^2", df: "\\nu" },
  "E.bilinear": { shape: "\\text{innovation shape}" }, "E.bistable-map": { crossings: null }, "E.cubic-crisis": { noise: "\\sigma" },
  "E.hmm": { dwell: "\\text{mean dwell}", k: "\\text{states}", mu: "\\mu_s", sd: "\\sigma_s", fwd: "\\text{forward prob.}" },
  "H.harmonic": { n_harmonics: "K", decay: "\\text{amplitude decay } a_k \\propto k^{-\\gamma}\\text{: } \\gamma" }, "E.random-coef-ar": { sigma_phi: "\\sigma_\\phi" },
  "E.markov-switching-ar": { mu: "\\mu_s", phi: "\\phi_s", sd: "\\sigma_s", k: "\\text{regimes}", dwell: "\\text{mean dwell}" },
  "E.setar": { phis: "\\phi^{(j)}", thresholds: "r_j", delay: "d" }, "E.star": { p1: "\\phi_1", p2: "\\phi_2" },
  "F.aperiodic-real": { width: "W" },
  "G.blinking-rotlet": { tau_switch: "\\tau" }, "G.bouncing-ball": { samples_per_period: "\\text{samples per period}" },
  "H.modulated-stationary": { depth: "m", mod_period: "1/f_m", deviation: "\\text{frequency deviation}", beat_period: "\\text{beat period}" },
  "H.quasiperiodic": { frequencies: "f_k" },
  "I.excitable-fhn": { spikes: null }, "I.heteroclinic": { dwell_time: null }, "I.stochastic-resonance": { forcing_period_samples: "2\\pi/\\omega" },
  "J.compound-poisson-increments": { rate: "\\lambda", tail: "\\alpha" }, "J.cox-smoothed": { mean: "\\bar\\lambda" },
  "J.hawkes": { base_rate: "\\mu", branching: "n", decay: "\\text{kernel decay}" },
  "J.markov-chain-emitted": { emission_sd: "\\sigma", k: "\\text{levels}", dwell: "\\text{mean dwell}" }, "J.poisson-smoothed": { rate: "\\lambda" },
  "J.renewal": { mean_interval: "\\mu_\\tau", target_B: "B" }, "J.telegraph-noisy": { noise_sd: "\\sigma", rate: "\\gamma" },
  "L.cyclostationary-switch": { phis: "\\phi(t)" }, "L.longlag-comb": { a: "\\text{AR coefficients}" }, "L.mixture": { ratio: "a" },
  "L.on-off": { a_critical: "a_c" },
  "N.bearing-vibration": { fault_period: "T_f", resonance: "\\omega_0" }, "N.collective": { T_over_Tc: "T/T_c" },
  "N.deboer": { gain: "G", resp_period: "T_{\\text{resp}}" }, "N.ecgsyn": { hr: "\\text{heart rate}", n_beats: null },
  "N.etas": { omori_p: "p" }, "N.gene-cell": { k_on: "k_{\\text{on}}", k_off: "k_{\\text{off}}" },
  "N.onoff-traffic": { n_sources: "M", tail: "\\alpha" }, "N.periodic-breathing": { hill_n: "n" },
  "N.richardson-weather-stationary": { p_ww: "p_{11}", p_wd: "p_{01}", shape: "k", scale: "\\theta" }, "N.river-discharge-stationary": { n_res: "n" },
  "N.rr-af": { atrial_rate: "\\lambda" }, "N.rr-ipfm": { T0: "T_0" }, "N.sir-seir": { R0: "R_0", amplitude: "\\beta_1" }, "N.speech": { f0: "f_0" },
};
const qkey = k => { const m = k.match(/^([A-Za-z]+)_([A-Za-z0-9]{1,2})$/);
  return QNAMES[k] || (QGREEK.has(k) ? "\\" + k : /^[A-Za-z]$/.test(k) ? k : /^[A-Za-z]\d$/.test(k) ? `${k[0]}_${k[1]}`
    : m && (QGREEK.has(m[1]) || m[1].length === 1) ? `${QGREEK.has(m[1]) ? "\\" + m[1] : m[1]}_{${m[2]}}` : `\\text{${k.replace(/_/g, " ")}}`); };
// an empty list (e.g. no MA terms: q = 0, so theta(B) = 1) gets no chip
const qval = (v, all = false) => Array.isArray(v) ? (v.length && v.every(u => typeof u === "number")
  ? `(${(all || v.length <= 4 ? v : v.slice(0, 4)).map(u => fmt(u)).join(",\\ ")}${!all && v.length > 4 ? ",\\ \\ldots" : ""})` : null)
  : typeof v === "number" ? fmt(v) : null;
function qparams(r, max = 6) {
  const eq = r.eqs && Object.keys(r.eqs.params).length, sym = QSYM[`${r.cls}.${r.family}`] || {};
  const list = eq ? Object.entries(r.eqs.params).map(([k, v]) => `${k.startsWith("\\") || /[_^{]/.test(k) || k.length === 1 ? k : qkey(k)} = ${+(+v).toPrecision(4)}`)
    : Object.entries(r.params).filter(([k]) => !QSKIP.has(k) && sym[k] !== null).map(([k, v]) => { const t = qval(v, max > 50); return t == null ? null : `${sym[k] || qkey(k)} = ${t}`; }).filter(Boolean);
  // generating parameters recorded as ground truth rather than drawn parameters (fGn's H, ARFIMA's d, ...)
  // (the period, timescale and event rate use the card's own symbol when its notation defines one)
  const where = (S.fam.get(`${r.cls}.${r.family}`).card?.where || []).join(" "), has = t => where.includes(`\\(${t}\\)`) || where.includes(`\\(${t},`);
  const truth = { hurst_H: "H", arfima_d: "d", spectral_beta: "\\beta", n_states: "\\text{states}",
    // period_samples is in samples: n_p where the card samples a period T (in the system's own time) n_p times
    period_samples: has("f_c") ? "1/f_c" : has("n_p") ? "n_p" : has("P") ? "P" : "\\text{period (samples)}", timescale_samples: has("\\tau") ? "\\tau" : "\\text{timescale}",
    event_rate: has("\\lambda") ? "\\lambda" : "\\text{event rate}" };
  const dup = lab => list.some(t => t.startsWith(lab + " =")) || (/period|^P$|^n_p$|^1\/f_c$/.test(lab) && list.some(t => /samples per period|period|^P =|^n_p =|^1\/f_c =/.test(t)));
  for (const [k, lab] of Object.entries(truth)) if (r.nums[k] != null && !dup(lab)) list.push(`${lab} = ${fmt(r.nums[k])}`);
  // measurement noise added on top of the dynamics, as a fraction of the clean series' s.d.
  if (r.nums.noise_sigma > 0 && !list.some(t => /noise/.test(t))) list.push(`\\text{measurement noise} = ${fmt(r.nums.noise_sigma)}`);
  return list.slice(0, max);
}
const qparHTML = (r, max) => { const L = qparams(r, max); return L.length ? `<span class="qc-par">${L.map(t => `<span data-itex="${esc(t)}"></span>`).join("")}</span>` : ""; };
function qcardHTML(id, { k = null, state = "", solo = false, answered = false, tag = "" } = {}) {
  const r = S.byId.get(id), card = S.fam.get(`${r.cls}.${r.family}`).card || {}, tex = qcardTex(r);
  const inner = `<span class="qc-top">${k != null ? `<span class="qkey">${k + 1}</span>` : ""}${mascot(r.cls, "sm")}<b>${esc(r.name)}</b></span>
    <span class="qc-desc">${esc(r.about || qfirst(card.description || ""))}</span>
    ${tex ? `<span class="qc-eq" data-tex="${esc(tex)}"></span>` : ""}
    ${qparHTML(r, 6)}`;
  return `<div class="qcard k-${r.cls}${solo ? " solo" : ""}${state ? " " + state : ""}" data-id="${id}">
    ${solo ? `<div class="qc-body">${inner}</div>` : `<button class="qc-pick" type="button" data-id="${id}"${answered ? " disabled" : ""}>${inner}</button>`}
    <div class="qc-foot">${tag}<button class="qc-more" type="button" data-info="${id}">Full details</button></div>
    ${solo ? "" : `<canvas class="qc-trace" aria-hidden="true"></canvas>`}
  </div>`;
}
// the whole family card (description, every equation, notation), without the series itself
function quizInfo(id) {
  const r = S.byId.get(id), card = S.fam.get(`${r.cls}.${r.family}`).card || {}, c = S.cls.get(r.cls);
  let d = $("#qinfo");
  if (!d) {
    d = document.createElement("dialog"); d.id = "qinfo"; d.setAttribute("aria-labelledby", "qi-title"); document.body.appendChild(d);
    d.addEventListener("click", e => { if (e.target === d || e.target.closest(".qi-close")) d.close(); });
  }
  d.className = `k-${r.cls}`;
  const eqs = r.eqs ? [`\\begin{aligned}${r.eqs.lines.join(" \\\\ ")}\\end{aligned}`] : (card.equations || []);
  d.innerHTML = `<div class="qi-head">${mascot(r.cls, "lg")}<div><div class="qi-kick">${esc(c.short)} · ${esc(c.name || c.title)}</div><h2 id="qi-title">${esc(r.name)}</h2></div>
      <button class="icon qi-close" type="button" aria-label="Close">×</button></div>
    <p>${esc(r.about || card.description || "")}</p>
    ${eqs.length ? `<div class="eq">${eqs.map(e => `<div data-tex="${esc(e)}"></div>`).join("")}</div>` : ""}
    ${whereFor(r, card).length ? `<ul class="where">${whereFor(r, card).map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}
    ${qparams(r, 99).length ? `<h3>This series' parameters</h3>${qparHTML(r, 99)}` : ""}
    ${r.about && card.description ? `<h3>The family</h3><p>${esc(card.description)}</p>` : ""}
    ${card.fixed ? `<h3>Fixed settings <span class="h3-sub">(all series in this family)</span></h3><ul class="where">${card.fixed.map(w => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}`;  // this series' values, not the family's sampling ranges
  if (window.katex) d.querySelectorAll("[data-itex]").forEach(el => katex.render(el.dataset.itex, el, { displayMode: false, throwOnError: false }));
  if (window.katex) d.querySelectorAll("[data-tex]").forEach(el => katex.render(el.dataset.tex, el, { displayMode: true, throwOnError: false }));
  mathify(d);
  d.showModal();
}

async function quizRender() {
  if (!location.hash.startsWith("#/quiz")) return;
  const score = Q.picks.filter(p => p.ok).length;
  let streak = 0; for (let k = Q.picks.length - 1; k >= 0 && Q.picks[k].ok; k--) streak++;
  const daily = Q.seed === qToday();
  const head = `
    <div class="qhead">
      <div><h1>Quiz</h1><p>${QMODES[Q.mode][1]} Normal mode puts the right answer among very different processes; devil mode among its closest look-alikes in hctsa feature space.</p></div>
      <div class="qctl">
        <span class="seg" role="group" aria-label="Mode">${Object.entries(QMODES).map(([k, [l]]) => `<button data-qmode="${k}" aria-pressed="${Q.mode === k}">${l}</button>`).join("")}</span>
        <span class="seg" role="group" aria-label="Difficulty">${["easy", "hard"].map(k => `<button data-qdiff="${k}" aria-pressed="${Q.diff === k}">${QDIFF[k]}</button>`).join("")}</span>
      </div>
    </div>
    <div class="qbar"><span>${daily ? `Today's round <span class="mono">${Q.seed}</span>` : "Random round"}</span>
      <span>Round <b>${Math.min(Q.i + 1, QN)}</b> / ${QN}</span><span>Score <b>${score}</b></span><span>Streak <b>${streak}</b></span>
      <button class="qsnd" id="q-snd" type="button" aria-pressed="${Sfx.on}" title="Mascot sound effects">${Sfx.on ? "Sound on" : "Sound off"}</button>
      <span class="qdots" aria-hidden="true">${Array.from({ length: QN }, (_, k) => {
        const p = Q.picks[k]; if (!p) return `<i class="${k === Q.i ? "cur" : ""}"></i>`;
        const cl = S.byId.get(Q.rounds[k].id).cls; return `<i class="m ${p.ok ? "y" : "n"} k-${cl}">${S.cls.get(cl).icon || ""}</i>`; }).join("")}</span></div>`;
  if (Q.i >= QN) { $("#view").innerHTML = `<div class="quiz">${head}${quizSummaryHTML()}</div>`; quizWire(); return; }
  const R = Q.rounds[Q.i], r = S.byId.get(R.id), answered = Q.picks.length > Q.i, P = Q.picks[Q.i];
  let body;
  const hideScope = Q.mode === "listen" && !answered;
  const viewbar = hideScope ? "" : `<div class="qviewbar">${qviewSeg()}<span class="qhint">${QVIEWS.find(v => v[0] === Q.view)[2]} Drag across a series to zoom.</span></div>`;
  if (Q.mode === "reverse") {
    body = `
      <div class="qsolo">${qcardHTML(R.id, { solo: true })}</div>
      <p class="qprompt">Which of these series did this process make?</p>${viewbar}
      <div class="qopts">${R.opts.map((id, k) => { const m = S.byId.get(id); return `
        <div class="qopt${answered ? ` k-${m.cls}` + (id === R.id ? " right" : id === P.pick ? " wrong" : "") : ""}">
          <div class="qo-head"><span class="qkey">${k + 1}</span>${answered ? `<a href="#" class="qo-name" data-open="${id}">${mascot(m.cls, "sm")}${esc(m.name)}</a>${id !== R.id ? qtier(R.id, id) : ""}` : ""}</div>
          <div class="qscope" data-sid="${id}"></div>
          <div class="qo-row"><button class="play qo-play" type="button" data-play="${id}"><span class="tri"></span>Listen</button>
            <button class="btn qo-pick" type="button" data-id="${id}"${answered ? " disabled" : ""}>Choose</button></div>
        </div>`; }).join("")}</div>`;
  } else {
    body = `
      <div class="qmystery${hideScope ? " veiled" : ""}">
        ${hideScope ? `<div class="qveil"><button class="play big" type="button" data-play="${R.id}"><span class="tri"></span>Listen</button><span>space to play</span></div>`
          : `<div class="qscope wide worm${answered ? " big" + (P.ok ? " fly" : " die") : ""}" data-sid="${R.id}" aria-label="The mystery series"></div>`}
      </div>
      <div class="qplayrow">${hideScope ? "" : `<button class="play" type="button" data-play="${R.id}"><span class="tri"></span>Listen</button>`}</div>
      <p class="qprompt">Which process made this series?</p>
      <div class="qcards">${R.opts.map((id, k) => qcardHTML(id, { k, answered, state: answered ? (id === R.id ? "right" : id === P.pick ? "wrong" : "other") : "", tag: answered && id !== R.id ? qtier(R.id, id) : "" })).join("")}</div>`;
  }
  const fb = answered ? quizFeedbackHTML(R, P) : "";
  $("#view").innerHTML = `<div class="quiz${answered ? " answered" : ""}">${head}<section class="qstage">${body}</section>${fb}</div>`;
  if (answered) $("#view").querySelectorAll(".qc-pick, .qo-pick").forEach(b => b.disabled = true);
  if (window.katex) $("#view").querySelectorAll("[data-tex]").forEach(el => katex.render(el.dataset.tex, el, { displayMode: true, throwOnError: false }));
  if (window.katex) $("#view").querySelectorAll("[data-itex]").forEach(el => katex.render(el.dataset.itex, el, { displayMode: false, throwOnError: false }));
  $("#view").querySelectorAll(".qc-eq").forEach(qfitEq);
  mathify($("#view"));
  quizWire();
  // the mystery stays in neutral ink (no class colour to give it away); reverse-mode options take theirs once answered
  const xs = await Promise.all(R.opts.map(seriesOf));
  if (Q.rounds[Q.i] !== R || !location.hash.startsWith("#/quiz")) return;
  $("#view").querySelectorAll(".qscope").forEach(el => {
    const id = el.dataset.sid, x = xs[R.opts.indexOf(id)];
    qscope(el, x, S.byId.get(id), qrgb(Q.mode === "reverse" && answered ? cink(el) : css("--trace")));
  });
  if (answered && Q.mode !== "reverse") $("#view").querySelectorAll(".qcard").forEach((b, k) => trace($(".qc-trace", b), xs[k], { color: cink(b) }));
}

// ---------- quiz scope: the series (drag to zoom), its phase portrait or its recurrence plot ----------
const QVIEWS = [["phase", "Phase portrait", "Phase portrait: x(t) against x(t + τ); loops and sheets suggest determinism, a round cloud noise."],
  ["rp", "Recurrence", "Recurrence plot: shaded where two delay-embedded states are close; diagonal lines mean determinism, isolated dots noise."],
  ["spec", "Spectrum", "Welch power spectrum, log–log; dashed: white noise of the same variance. Flat: no memory; falling: correlated; peaks: periodic."]];
const qviewSeg = () => `<span class="seg sm" role="group" aria-label="Phase-space view">${QVIEWS.map(([k, l, d]) =>
  `<button type="button" data-qview="${k}" aria-pressed="${Q.view === k}" title="${esc(d)}">${l}</button>`).join("")}</span>`;
// the recurrence plot parses its colour as rgb(): resolve any CSS colour (hex, oklch, ...) through the browser
const qrgb = c => { const el = document.createElement("i"); el.style.color = c; document.body.appendChild(el); const v = getComputedStyle(el).color; el.remove(); return v; };
// the series (drag to zoom, double-click to reset) beside its phase portrait or recurrence plot; the wide
// (mystery) layout carries its own phase-space toggle, the reverse-mode options share the one above them
// A pastel-rainbow worm inches along the mystery series (twice the size and speed once the round is answered), left to right, riding
// on the line (in the zoomed window if there is one). Its segments are spaced by distance along the drawn curve,
// so it climbs spikes in one piece. Its head is remembered as a sample index (Q.wormAt), so a zoom, a reset or a
// re-render picks up where it was; if a zoom leaves it outside the window it starts again at the window's left edge.
// fly (a right answer): it sprouts wings, crawls on for a moment, then takes off, climbing ever faster up and to the
// right with its body following the head's flight path, out through the top of the plot (its canvas reaches SKY px
// above the series for this). It stops by itself once it has flown away or its canvas leaves the page.
const SKY = 180;
// die (a wrong answer): once the plot is on screen it freezes with a shudder, drains to grey with crossed-out eyes,
// then tumbles off the line and falls out through the bottom (its canvas reaches PIT px below the series for this).
const PIT = 360;
function qworm(cv, x, getPlot, z = 1, fly = false, isGlow = () => false, die = false, st = Q) {  // st: whose wormAt (and run token)  // z: size and speed factor (2 once the round is answered)
  const N = 48, SEP = 1.8 * z, t0 = performance.now(), OFF = fly ? SKY : 0;  // beads overlap; a body line bridges the thin tail
  let s = 0, last = t0, crawl = 0, size = null, path = null, key = "", hist = null, takeoff = null;
  // a right answer is usually clicked down among the cards: the flight clock only starts once the plot is on screen
  // (at least half visible), so the take-off isn't over before anyone scrolls back up to see it
  let seenAt = fly || die ? null : t0, flyT = 0, dead = null;
  const trail = [];  // glow mode: [sample index, time] of the head, drawn as a fading neon line
  if (fly || die) {
    const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { seenAt = seenAt ?? performance.now(); io.disconnect(); } }, { threshold: .5 });
    io.observe(cv.parentElement);
  }
  const run = st.run;
  const frame = now => {
    if (!cv.isConnected || st.run !== run) return;  // (the series pop-up stops its worm by bumping st.run)
    const P = getPlot(); if (!P) return requestAnimationFrame(frame);
    const rc = cv.getBoundingClientRect();
    if (!size || size[1] !== rc.width || size[2] !== rc.height) size = [...fit(cv)];  // resize the backing store only when the box changes
    const [g, W, H] = size, k = `${P.a},${P.b},${W},${H}`;
    if (k !== key) {  // the drawn curve as a polyline with cumulative arc length
      key = k; const pts = [], cum = [0];
      for (let i = P.a; i <= P.b; i++) pts.push([P.X(i - P.a), P.Y(x[i]) + OFF]);
      for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      path = { pts, cum, L: cum[cum.length - 1] };
      const h = st.wormAt - P.a;  // same sample as before, in the new window's arc length
      s = h > 0 && h < pts.length - 1 ? cum[Math.floor(h)] + (h % 1) * (cum[Math.floor(h) + 1] - cum[Math.floor(h)]) : 0;
      hist = null;
    }
    const pos = d => {  // point at arc length d (binary search); past the end, straight on to the right
      const { pts, cum, L } = path; if (d <= 0) return pts[0];
      if (d >= L) { const e = pts[pts.length - 1]; return [e[0] + (d - L), e[1]]; }
      let lo = 0, hi = cum.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (cum[m] < d) lo = m; else hi = m; }
      const f = (d - cum[lo]) / ((cum[hi] - cum[lo]) || 1); return [pts[lo][0] + f * (pts[hi][0] - pts[lo][0]), pts[lo][1] + f * (pts[hi][1] - pts[lo][1])];
    };
    // inchworm gait: the speed pulses, so it lunges and pauses; after an answer (z = 2) it barely pauses and is faster
    const dt = Math.max(0, Math.min(64, now - last)); last = now;  // (a first frame can be stamped just before t0) crawl += dt / 1000;
    const floor = z > 1 ? .6 : .2, base = 130 * z * (z > 1 ? 1.5 : 1.3);  // px of curve per second, before the gait
    // hybrid pace: a steady crawl along the curve, but never slower through time than the whole series in CROSS s.
    // A rough series has far more curve per sample, so it gets sped up; smooth ones keep their pace. The gait's mean
    // factor is floor + 1.6 E[max(0, sin)^2] = floor + 0.4.
    const CROSS = 60, perSample = path.L / Math.max(1, P.b - P.a), boost = Math.max(1, perSample * x.length / CROSS / (base * (floor + .4)));
    s += base * boost * (dt / 1000) * (floor + 1.6 * Math.max(0, Math.sin(crawl * 4.5)) ** 2);
    if (!fly && !dead && s - SEP * (N - 1) > path.L) { s = 0; st.wormAt = P.b >= x.length - 1 ? 0 : P.a; key = ""; return requestAnimationFrame(frame); }
    if (!takeoff && !dead) {
      const { cum } = path; let lo = 0, hi = cum.length - 1;  // where the head is, as a fractional sample index
      if (s >= path.L) st.wormAt = P.a + hi; else { while (hi - lo > 1) { const m = (lo + hi) >> 1; if (cum[m] < s) lo = m; else hi = m; }
        st.wormAt = P.a + lo + (s - cum[lo]) / ((cum[hi] - cum[lo]) || 1); }
    }
    const rad = j => {  // a big head, a slim neck, a peristaltic body, a tapered tail
      if (j === 0) return 5.6 * z;
      if (j <= 2) return 2.35 * z;
      const u = j / (N - 1), taper = u < .5 ? 1 : 1 - 1.2 * (u - .5);
      return 2.6 * z * taper * (1 + .2 * Math.sin(j * .425 - crawl * 7));
    };
    // segment centres: along the curve when crawling; along the head's own trail when flying
    let place;
    if (!fly) place = j => { const d = s - j * SEP; if (d < 0 || d > path.L) return null; const [px, py] = pos(d); return [px, py - rad(j) + 1]; };
    else {
      if (seenAt != null) flyT += dt / 1000;  // flight time counts only while the plot has been seen
      if (!takeoff && s - SEP * (N - 1) > path.L) { s = 0; hist = null; }  // still grounded: loop like a crawling worm
      const tf = flyT, [cx, cy] = pos(s);
      if (!hist) { hist = []; for (let j = N - 1; j >= 1; j--) { const d = Math.max(0, s - j * SEP); const [px, py] = pos(d); hist.push([px, py]); } }
      let hx = cx, hy = cy;
      if (tf > 1.2 && !takeoff) takeoff = [cx, cy, s];
      if (takeoff) {  // airborne: it leaves the line and flies its own path, forward and ever more steeply up
        const u = tf - 1.2;
        hx = takeoff[0] + 70 * u + 12 * u * u;
        hy = takeoff[1] - 20 * u - 38 * u ** 1.9;
        s = takeoff[2];  // the crawl along the curve stops here
      }
      hist.push([hx, hy]); if (hist.length > 600) hist.splice(0, hist.length - 600);
      place = j => {  // walk back along the trail j * SEP px
        let need = j * SEP, q = hist.length - 1;
        while (q > 0) { const [ax, ay] = hist[q], [bx, by] = hist[q - 1], l = Math.hypot(ax - bx, ay - by);
          if (l >= need) { const f = need / (l || 1); return [ax + f * (bx - ax), ay + f * (by - ay) - rad(j) + 1]; } need -= l; q--; }
        return [hist[0][0], hist[0][1] - rad(j) + 1];
      };
    }
    g.clearRect(0, 0, W, H);
    const glow = isGlow();
    if (glow) {
      const TAU = 2.4, at = i => { const j = Math.max(0, Math.min(x.length - 1, Math.floor(i))), f = i - j; return x[j] * (1 - f) + x[Math.min(j + 1, x.length - 1)] * f; };
      if (!trail.length || Math.abs(st.wormAt - trail[trail.length - 1][0]) > .25) trail.push([st.wormAt, now]);
      while (trail.length && now - trail[0][1] > 7000) trail.shift();
      g.lineCap = g.lineJoin = "round";
      for (const [lw, k] of [[7, .22], [1.8, 1]]) {  // a soft halo, then the bright core
        for (let q = 1; q < trail.length; q++) {
          const [i0] = trail[q - 1], [i1, t1] = trail[q];
          if (Math.abs(i1 - i0) > 5 || i0 < P.a || i1 > P.b) continue;  // skip the jump when it loops back to the start
          g.strokeStyle = `rgba(90, 255, 70, ${k * Math.exp(-(now - t1) / 1000 / TAU)})`; g.lineWidth = lw;
          g.beginPath(); g.moveTo(P.X(i0 - P.a), P.Y(at(i0)) + OFF); g.lineTo(P.X(i1 - P.a), P.Y(at(i1)) + OFF); g.stroke();
        }
      }
    } else trail.length = 0;
    const hue0 = (now - t0) / 40;
    let seg = [], grey = 0;
    for (let j = 0; j < N; j++) { const p = place(j); if (p) seg.push([p[0], p[1], j]); }
    if (die && seenAt != null && seg.length) {  // freeze, shudder and grey out, then tumble and fall
      if (!dead) dead = { t: now, seg: seg.map(q => [...q]), spin: Math.random() < .5 ? -1 : 1 };
      const te = (now - dead.t) / 1000, ft = Math.max(0, te - 1);
      const cx = dead.seg.reduce((a, q) => a + q[0], 0) / dead.seg.length, cy = dead.seg.reduce((a, q) => a + q[1], 0) / dead.seg.length;
      const ang = dead.spin * (ft * 1.2 + .6 * ft * ft), c = Math.cos(ang), sn = Math.sin(ang);
      const shake = te < 1 ? Math.sin(te * 70) * 1.8 * (1 - te) : 0, dy = 380 * ft * ft, dx = dead.spin * 22 * ft;
      seg = dead.seg.map(([px, py, j]) => { const rx = px - cx, ry = py - cy; return [cx + rx * c - ry * sn + shake + dx, cy + rx * sn + ry * c + dy, j]; });
      grey = Math.min(1, te / .7);
      if (seg.every(([, py]) => py > H + 30)) return;  // gone
    }
    if (takeoff && seg.every(([px, py]) => py < -12 || px > W + 12)) return;  // flown away
    const wings = (front) => {  // two flapping, translucent wings over the fifth bead, growing in as they sprout
      if (!fly || seg.length < 6) return;
      const grow = Math.min(1, .15 + flyT / .6), [wx, wy] = seg[4], flap = Math.sin(now / 22) * .7;
      g.save(); g.translate(wx, wy - 2 * z);
      g.rotate((front ? -1.05 : -1.45) + flap * (front ? 1 : .8));
      if (glow) { g.fillStyle = front ? "rgba(150,255,130,.4)" : "rgba(120,255,100,.25)"; g.strokeStyle = "#8dff6e"; g.shadowColor = "#4dff2e"; g.shadowBlur = 10; }
      else { g.fillStyle = front ? "rgba(255,255,255,.8)" : "rgba(235,240,255,.65)"; g.strokeStyle = `hsl(${(hue0 + 200) % 360} 55% 65%)`; }
      g.lineWidth = 1;
      g.beginPath(); g.ellipse(0, -8 * z * grow, 4.2 * z * grow, 9 * z * grow, 0, 0, 7); g.fill(); g.stroke();
      g.restore();
    };
    wings(false);
    const col = (j, L) => glow ? `hsl(${112 + j * .5} ${100 * (1 - .8 * grey)}% ${(L - 12 - j * .35) * (1 - .45 * grey)}%)` : `hsl(${(hue0 + j * 8) % 360} ${(L > 75 ? 85 : 60) * (1 - .9 * grey)}% ${L - 8 * grey}%)`;
    if (glow) { g.shadowColor = "#4dff2e"; g.shadowBlur = 10 * (1 - grey); }  // a dying glow worm's light goes out
    if (seg.length > 1) {  // body line under the beads, so the worm always reads as one piece
      g.lineCap = g.lineJoin = "round";
      for (let q = 1; q < seg.length; q++) {
        g.strokeStyle = col(seg[q][2], 70); g.lineWidth = 2 * rad(seg[q][2]) - .5;
        g.beginPath(); g.moveTo(seg[q - 1][0], seg[q - 1][1]); g.lineTo(seg[q][0], seg[q][1]); g.stroke();
      }
    }
    for (let q = seg.length - 1; q >= 0; q--) {
      const [px, py, j] = seg[q], r = rad(j);
      g.fillStyle = col(j, 80); g.strokeStyle = glow ? "rgba(200,255,190,.8)" : `hsl(${(hue0 + j * 8) % 360} ${45 * (1 - grey)}% 60%)`; g.lineWidth = .5;
      g.beginPath(); g.arc(px, py, r, 0, 7); g.fill(); g.stroke();
      if (j === 0) g.shadowBlur = 0;
      if (j === 0 && dead) {  // crossed-out eyes
        g.strokeStyle = glow ? "#d8e8d4" : "#333"; g.lineWidth = .9 * z;
        for (const [ex, ey] of [[1.6 * z, -2.9 * z], [4 * z, -1.1 * z]]) {
          const e = 1.3 * z; g.beginPath(); g.moveTo(px + ex - e, py + ey - e); g.lineTo(px + ex + e, py + ey + e); g.moveTo(px + ex + e, py + ey - e); g.lineTo(px + ex - e, py + ey + e); g.stroke();
        }
      } else if (j === 0) {  // eyes, looking the way it crawls
        for (const [ex, ey] of [[1.6 * z, -2.9 * z], [4 * z, -1.1 * z]]) {
          g.fillStyle = "#fff"; g.beginPath(); g.arc(px + ex, py + ey, 1.9 * z, 0, 7); g.fill();
          g.fillStyle = "#222"; g.beginPath(); g.arc(px + ex + .6 * z, py + ey, 1 * z, 0, 7); g.fill();
        }
      }
    }
    wings(true);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}
// The worm's place in phase space, on an overlay (pov) over the phase-space canvas (ps): its delay vector with a
// short rainbow trail on the phase portrait, or its time on the recurrence plot's diagonal; in glow mode a dark panel
// where only its recent path (or, for the spectrum, the whole spectrum) glows. Shared by the quiz and the series pop-up.
// o: { view, glow, gone, trail (persistent array), at (the worm's sample index), sz (persistent { v } size cache) }
function wormPov(pov, ps, x, tau, o) {
    const rc = pov.getBoundingClientRect(); if (!rc.width) return;
  if (!o.sz.v || o.sz.v[1] !== rc.width || o.sz.v[2] !== rc.height) o.sz.v = [...fit(pov)];
  const [g, W, H] = o.sz.v, n = x.length, i = Math.round(o.at);
  g.clearRect(0, 0, W, H);
  const gone = o.gone;  // the worm has left (or fallen off) the series: no new place in phase space to mark
  if (gone && !o.glow) return;
  if (o.glow) {  // dark panel: the attractor appears only where the worm's delay vector has recently been
    const now = performance.now(), TAU = 2.4;
    if (!gone && (!o.trail.length || o.trail[o.trail.length - 1][0] !== i)) o.trail.push([i, now]);
    while (o.trail.length && now - o.trail[0][1] > 7000) o.trail.shift();
    g.lineCap = g.lineJoin = "round";
    if (o.view === "spec") {  // no time axis for the worm to light: the whole spectrum, fixed, in neon
      spectrum(pov, x, "#6dff4f", { axis: "rgba(140,255,120,.65)", grid: "rgba(90,255,70,.2)", glow: "#4dff2e" }); o.sz.v = null;
      return;
    }
    if (o.view === "phase") {
      const [lo, hi] = range(x), pad = 18, X = v => pad + (v - lo) / (hi - lo) * (W - 2 * pad), Y = v => H - pad - (v - lo) / (hi - lo) * (H - 2 * pad);
      g.strokeStyle = "rgba(90, 255, 70, .14)"; g.lineWidth = 1; g.strokeRect(pad, pad, W - 2 * pad, H - 2 * pad);
      for (const [lw, k] of [[6, .2], [1.6, 1]]) for (let q = 1; q < o.trail.length; q++) {
        const [a] = o.trail[q - 1], [b, tb] = o.trail[q];
        if (Math.abs(b - a) > 3 || b + tau >= n || a < 0) continue;
        g.strokeStyle = `rgba(90, 255, 70, ${k * Math.exp(-(now - tb) / 1000 / TAU)})`; g.lineWidth = lw;
        g.beginPath(); g.moveTo(X(x[a]), Y(x[a + tau])); g.lineTo(X(x[b]), Y(x[b + tau])); g.stroke();
      }
      if (!gone && i + tau < n) { g.shadowColor = "#4dff2e"; g.shadowBlur = 12; g.fillStyle = "#b9ff9f"; g.beginPath(); g.arc(X(x[i]), Y(x[i + tau]), 4, 0, 7); g.fill(); g.shadowBlur = 0; }
    } else {  // the recurrence plot lit up only for times the worm has reached: it builds from the bottom-left
      const N = n - 2 * tau, f = Math.min(1, (i + .5) / N);
      g.save(); g.beginPath(); g.rect(0, (1 - f) * H, f * W, f * H); g.clip();
      g.imageSmoothingEnabled = false; g.drawImage(ps, 0, 0, ps.width, ps.height, 0, 0, W, H); g.restore();
      if (!gone && i < N) { g.shadowColor = "#4dff2e"; g.shadowBlur = 12; g.fillStyle = "#b9ff9f"; g.beginPath(); g.arc(f * W, (1 - f) * H, 4, 0, 7); g.fill(); g.shadowBlur = 0; }
    }
    return;
  } else o.trail.length = 0;
  if (o.view === "spec") return;  // a spectrum has no time axis: nothing for the worm to mark
  const dot = (px, py, r, hue) => { g.fillStyle = `hsl(${hue} 85% 78%)`; g.strokeStyle = `hsl(${hue} 50% 45%)`; g.lineWidth = 1.2; g.beginPath(); g.arc(px, py, r, 0, 7); g.fill(); g.stroke(); };
  if (o.view === "phase") {  // same frame as phasePortrait: 18 px pad, x range on both axes
    const [lo, hi] = range(x), pad = 18, X = v => pad + (v - lo) / (hi - lo) * (W - 2 * pad), Y = v => H - pad - (v - lo) / (hi - lo) * (H - 2 * pad);
    const T = 14, pts = [];
    for (let k = T; k >= 0; k--) { const t = i - k; if (t >= 0 && t + tau < n) pts.push([X(x[t]), Y(x[t + tau]), k]); }
    g.strokeStyle = css("--ink-3"); g.globalAlpha = .6; g.lineWidth = 1; g.beginPath();
    pts.forEach(([px, py], q) => q ? g.lineTo(px, py) : g.moveTo(px, py)); g.stroke(); g.globalAlpha = 1;
    pts.forEach(([px, py, k]) => dot(px, py, k ? 2.6 - 1.4 * k / T : 5.2, (k * 22) % 360));
  } else {  // recurrence plot: time runs up the diagonal, bottom-left to top-right
    const N = n - 2 * tau; if (i >= N) return;
    const f = (i + .5) / N, px = f * W, py = (1 - f) * H;
    g.strokeStyle = css("--ink-3"); g.globalAlpha = .5; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(px, 0); g.lineTo(px, H); g.moveTo(0, py); g.lineTo(W, py); g.stroke();
    g.setLineDash([]); g.globalAlpha = 1; dot(px, py, 5, 0);
  }
}
// one phase-space view for every plot on the page, so options compare like with like
function qsetView(k) {
  Q.view = k; const v = $("#view");
  v.querySelectorAll("[data-qview]").forEach(o => o.setAttribute("aria-pressed", o.dataset.qview === k));
  const h = $(".qhint", v); if (h) h.textContent = QVIEWS.find(q => q[0] === k)[2] + " Drag across a series to zoom.";
  v.querySelectorAll(".qscope").forEach(el => el.qdraw && el.qdraw());
}
function qscope(el, x, r, color) {
  const id = r.id, tau = r.step || acfTau(x);  // a map's own step (tau = 1), else the ACF 1/e delay, as in the series pop-up
  const wide = el.classList.contains("wide");
  const worm = el.classList.contains("worm") && !matchMedia("(prefers-reduced-motion: reduce)").matches, fly = el.classList.contains("fly"), die = el.classList.contains("die");
  const big = el.classList.contains("big");
  // framing (global / journey) and lighting (glow worm) are separate toggles, both kept through an answer
  const journeySeg = !worm ? "" : `<button type="button" class="qtoggle" data-journey aria-pressed="${Q.sview === "journey"}" title="Zoom in on the 200 samples around the worm and follow it">Journey view</button>`
    + `<button type="button" class="qglow" data-glow aria-pressed="${Q.glow}" title="Dark mode: only the worm's fading neon trail lights the series">Glow worm</button>`;
  el.innerHTML = `<div class="qs-s"><div class="qs-wrap"><canvas class="qs-series"></canvas>${worm ? `<canvas class="qs-worm${fly ? " sky" : die ? " pit" : ""}" aria-hidden="true"></canvas>` : ""}</div>
      <div class="qs-under">${journeySeg}<span class="qs-note"></span></div></div>
    <div class="qs-p">${wide ? qviewSeg() : ""}<div class="qs-pwrap"><canvas class="qs-ps"></canvas>${worm ? `<canvas class="qs-pov" aria-hidden="true"></canvas>` : ""}</div><div class="qs-pnote"></div></div>`;
  const cv = $(".qs-series", el), note = $(".qs-note", el), ps = $(".qs-ps", el), pnote = $(".qs-pnote", el);
  // journey view: the JOURNEY samples around the worm's head, following it; else the drag zoom, else everything
  // journey view stays on through an answer: the window follows the worm until it takes off or dies, then holds
  // still (Q.wormAt stops moving) while it flies away or falls
  const JOURNEY = 200, journey = () => worm && Q.sview === "journey";
  // glow worm: the series is dark and invisible; only the neon worm and its fading trail light it up (until answered)
  const glow = () => worm && Q.glow;
  const span = () => {
    if (journey()) { const a = Math.max(0, Math.min(x.length - 1 - JOURNEY, Math.round(Q.wormAt) - JOURNEY / 2)); return [a, a + JOURNEY]; }
    return Q.zooms[id] || [0, x.length - 1];
  };
  let plot = null;
  const drawSeries = sel => {
    const [a, b] = span(), P = trace(cv, x.slice(a, b + 1), { color, pad: 6, lw: 1.1 });
    plot = { a, b, X: P.X, Y: P.Y };
    el.classList.toggle("glowing", glow());
    if (glow()) P.g.clearRect(0, 0, P.W, P.H);
    if (sel) { P.g.fillStyle = color; P.g.globalAlpha = .12; P.g.fillRect(Math.min(sel[0], sel[1]), 0, Math.abs(sel[1] - sel[0]), P.H); P.g.globalAlpha = 1; }
    note.innerHTML = journey() ? `t = ${a}–${b}${glow() ? "" : ", following the worm"}` : glow() ? "only the glow worm's trail lights the series" : Q.zooms[id] ? `t = ${a}–${b} · <button type="button" class="rz">reset zoom</button>` : "drag across to zoom";
  };
  const drawPS = () => {
    el.dataset.view = Q.view;
    if (Q.view === "phase") { phasePortrait(ps, x, color, tau); pnote.textContent = `τ = ${tau}`; }
    else if (Q.view === "spec") { spectrum(ps, x, color); pnote.textContent = "Welch, 256-sample segments"; }
    else { const [g] = fit(ps); g.setTransform(1, 0, 0, 1, 0, 0); recurrence(ps, x, glow() ? "rgb(90, 255, 70)" : color, tau); pnote.textContent = `m = 3, τ = ${tau}`; }
  };
  const px = e => e.clientX - cv.getBoundingClientRect().left;
  const idx = p => { const [a, b] = span(); return Math.max(a, Math.min(b, a + Math.round(p / cv.getBoundingClientRect().width * (b - a)))); };
  let drag = null;
  cv.onpointerdown = e => { if (e.button > 0 || journey()) return; drag = { x0: px(e), x1: px(e) }; cv.setPointerCapture(e.pointerId); };
  cv.onpointermove = e => { if (drag) { drag.x1 = px(e); drawSeries([drag.x0, drag.x1]); } };
  cv.onpointerup = cv.onpointercancel = () => {
    const d = drag; drag = null; if (!d) return;
    if (Math.abs(d.x1 - d.x0) > 6) { const i0 = idx(Math.min(d.x0, d.x1)), i1 = idx(Math.max(d.x0, d.x1)); if (i1 - i0 >= 10) Q.zooms[id] = [i0, i1]; }
    drawSeries();
  };
  cv.ondblclick = () => { delete Q.zooms[id]; drawSeries(); };
  note.onclick = e => { if (e.target.closest(".rz")) { delete Q.zooms[id]; drawSeries(); } };
  el.querySelectorAll("[data-qview]").forEach(b => b.onclick = () => qsetView(b.dataset.qview));
  el.qdraw = drawPS;
  drawSeries(); drawPS();
  el.querySelectorAll("[data-journey]").forEach(b => b.onclick = () => {
    Q.sview = Q.sview === "journey" ? "global" : "journey";
    b.setAttribute("aria-pressed", Q.sview === "journey");
    drawSeries();
  });
  el.querySelectorAll("[data-glow]").forEach(b => b.onclick = () => {
    Q.glow = !Q.glow; b.setAttribute("aria-pressed", Q.glow);
    if (Q.glow) {  // the glow worm starts in journey view (it can still be switched back to the whole series)
      Q.sview = "journey"; el.querySelectorAll("[data-journey]").forEach(j => j.setAttribute("aria-pressed", true));
    }
    drawSeries(); drawPS(); discoSync();
  });
  // the worm's place in phase space: its current delay vector (with a short rainbow trail) on the phase portrait,
  // or its time on the recurrence plot's diagonal
  const pov = $(".qs-pov", el), povTrail = [], povSz = { v: null };
  const drawPov = () => wormPov(pov, ps, x, tau, { view: Q.view, glow: glow(), gone: fly || die, trail: povTrail, at: Q.wormAt, sz: povSz });
  // in journey view the window moves with the worm: redraw the series whenever the window slides
  if (worm) qworm($(".qs-worm", el), x, () => { if (journey() && (!plot || plot.a !== span()[0])) drawSeries(); drawPov(); return plot; }, big ? 2 : 1, fly, glow, die);
  discoSync();
}

// how alike a wrong option is to the answer, as a tag: tiers set against the median nearest-neighbour distance
// (61 here) and the 16 nearest other-family series kept in quiz.json (the 16th typically sits ~75 away)
function qtier(a, b) {
  const d = qdist(a, b), med = S.quiz.median_nn;
  const [k, label] = d == null ? ["far", "Far apart"] : d < med ? ["near", "Near match"] : d < 1.12 * med ? ["close", "Close match"] : ["loose", "Loose match"];
  const tip = d == null ? "Not among the answer's closest look-alikes in hctsa feature space"
    : `${d} apart in hctsa feature space (a typical series' nearest neighbor sits ${med} away)`;
  return `<span class="qtag ${k}" title="${tip}">${label}</span>`;
}
function quizFeedbackHTML(R, P) {
  const r = S.byId.get(R.id);
  const c = S.cls.get(r.cls);
  return `<div class="qfb ${P.ok ? "y" : "n"}" role="status">
    <button class="qfb-pet k-${r.cls} ${P.ok ? "hop" : "droop"}" type="button" data-call="${r.cls}" title="Hear the ${esc(c.mascot)} again">${mascot(r.cls, "xl")}</button>
    <div class="qfb-main"><b>${P.ok ? "Right." : "Not this time."}</b> ${P.ok ? "It was" : "The answer was"} <a href="#" data-open="${R.id}">${esc(r.name)}</a>${Q.mode === "reverse" ? "'s series" : ""}.
      <span class="qfb-sub">Tags on the other options show how alike they are to the answer in hctsa feature space.</span></div>
    <button class="btn primary" id="q-next" type="button">${Q.i + 1 < QN ? "Next" : "See results"} <span aria-hidden="true">→</span></button>
  </div>`;
}

function quizSummaryHTML() {
  const score = Q.picks.filter(p => p.ok).length, key = `${Q.mode}.${Q.diff}`;
  const best = store.get("best", {}); const prev = best[key] || 0;
  if (!Q.saved) {  // record once per finished session: best score and per-class tallies across sessions
    Q.saved = true; if (score > prev) { best[key] = score; store.set("best", best); }
    const tally = store.get("tally", {});
    Q.picks.forEach((p, k) => { const c = S.byId.get(Q.rounds[k].id).cls, t = tally[c] || [0, 0]; tally[c] = [t[0] + (p.ok ? 1 : 0), t[1] + 1]; });
    store.set("tally", tally);
  }
  const tally = store.get("tally", {});
  const rows = Q.rounds.map((R, k) => { const r = S.byId.get(R.id), c = S.cls.get(r.cls), t = tally[r.cls];
    return `<tr class="k-${r.cls}"><td>${Q.picks[k].ok ? "✓" : "✗"}</td><td>${mascot(r.cls, "sm")} ${esc(c.name || c.title)}</td>
      <td><a href="#" data-open="${R.id}">${esc(r.name)}</a></td><td class="mono">${t ? `${t[0]}/${t[1]}` : ""}</td></tr>`; }).join("");
  return `<section class="qsum">
    <div class="qsum-score"><b>${score}</b><span>/ ${QN}</span></div>
    <div class="qzoo">${Q.rounds.map((R, k) => { const cl = S.byId.get(R.id).cls, c = S.cls.get(cl);
      return `<button class="qz ${Q.picks[k].ok ? "y" : "n"} k-${cl}" type="button" data-call="${cl}" title="${esc(c.mascot)} (${esc(c.short)})${Q.picks[k].ok ? "" : ": missed"}">${mascot(cl, "lg")}</button>`; }).join("")}</div>
    <p class="qzoo-cap">You caught ${score} of the ${QN} mascots${score < QN ? "; the gray ones got away" : ""}. Tap one to hear it.</p>
    <p>${QMODES[Q.mode][0]}, ${QDIFF[Q.diff].toLowerCase()}${score > prev ? " · a new best" : prev ? ` · your best is ${Math.max(prev, score)}` : ""}.</p>
    <div class="qsum-act">
      <button class="btn primary" id="q-share" type="button">Copy result</button>
      <button class="btn" id="q-random" type="button">Play a random round</button>
      ${Q.seed === qToday() ? "" : `<button class="btn" id="q-daily" type="button">Today's round</button>`}
    </div>
    <textarea id="q-sharetext" readonly hidden></textarea>
    <table class="qtab"><thead><tr><th></th><th>Class</th><th>Series</th><th title="right / played, all sessions in this browser">All time</th></tr></thead><tbody>${rows}</tbody></table>
  </section>`;
}
const QEMOJI = { goldfish: "🐟", jellyfish: "🪼", stingray: "🐠", elephant: "🐘", chameleon: "🦎", frog: "🐸", butterfly: "🦋",
  firefly: "✨", bee: "🐝", woodpecker: "🐦", octopus: "🐙", owl: "🦉", beaver: "🦫" };
function quizShareText() {
  const score = Q.picks.filter(p => p.ok).length;
  return `1000×1000 quiz · ${Q.seed === qToday() ? Q.seed : "random round"} · ${QMODES[Q.mode][0]}, ${QDIFF[Q.diff].toLowerCase()} · ${score}/${QN}\n${Q.picks.map((p, k) => p.ok ? (QEMOJI[S.cls.get(S.byId.get(Q.rounds[k].id).cls).mascot] || "🟩") : "⬛").join("")}`;
}

function quizAnswer(id) {
  if (Q.i >= QN || Q.picks.length > Q.i) return;
  Audio.stop(); Q.playing = null;
  const ok = id === Q.rounds[Q.i].id;
  Q.picks.push({ pick: id, ok });
  Sfx.play(S.cls.get(S.byId.get(Q.rounds[Q.i].id).cls).mascot, ok);
  quizRender();
}
function quizNext() { Audio.stop(); Q.playing = null; Q.zooms = {}; Q.wormAt = 0; Q.i++; quizRender(); window.scrollTo({ top: 0 }); }
async function quizPlay(id, btn) {
  if (Q.playing === id) { Audio.stop(); return; }
  const r = S.byId.get(id), x = await seriesOf(id);
  document.querySelectorAll(".quiz .play").forEach(b => b.classList.remove("on"));
  Q.playing = id; btn && btn.classList.add("on");
  Audio.play(x, r, Audio.defaultMode(r), { done: () => { if (Q.playing === id) Q.playing = null; btn && btn.classList.remove("on"); } });
}
function quizWire() {
  const v = $("#view");
  v.querySelectorAll("[data-qmode]").forEach(b => b.onclick = () => { Q.mode = b.dataset.qmode; quizStart(Q.seed); quizRender(); });
  v.querySelectorAll("[data-qdiff]").forEach(b => b.onclick = () => { Q.diff = b.dataset.qdiff; quizStart(Q.seed); quizRender(); });
  v.querySelectorAll(".qc-pick, .qo-pick").forEach(b => b.onclick = () => quizAnswer(b.dataset.id));
  v.querySelectorAll("[data-qview]").forEach(b => b.onclick = () => qsetView(b.dataset.qview));
  v.querySelectorAll("[data-info]").forEach(b => b.onclick = () => quizInfo(b.dataset.info));
  v.querySelectorAll("[data-call]").forEach(b => b.onclick = () => Sfx.play(S.cls.get(b.dataset.call).mascot, true, { chime: false }));
  const sn = $("#q-snd"); if (sn) sn.onclick = () => { Sfx.on = !Sfx.on; store.set("sound", Sfx.on); sn.setAttribute("aria-pressed", Sfx.on); sn.textContent = Sfx.on ? "Sound on" : "Sound off"; discoSync(); };
  v.querySelectorAll("[data-play]").forEach(b => b.onclick = e => { e.stopPropagation(); quizPlay(b.dataset.play, b); });
  v.querySelectorAll("[data-open]").forEach(a => a.onclick = e => { e.preventDefault(); Audio.stop(); openSeries(a.dataset.open, false); });
  const nx = $("#q-next"); if (nx) { nx.onclick = quizNext; nx.focus({ preventScroll: true }); }
  const rs = $("#q-random"); if (rs) rs.onclick = () => { quizStart(Math.random().toString(36).slice(2, 8)); quizRender(); };
  const dl = $("#q-daily"); if (dl) dl.onclick = () => { quizStart(qToday()); quizRender(); };
  const sh = $("#q-share"); if (sh) sh.onclick = async () => {
    const t = quizShareText();
    try { await navigator.clipboard.writeText(t); sh.textContent = "Copied"; }
    catch { const ta = $("#q-sharetext"); ta.hidden = false; ta.value = t; ta.select(); sh.textContent = "Select and copy"; }
  };
}
addEventListener("keydown", e => {
  if (!location.hash.startsWith("#/quiz") || $("#modal").open || ($("#qinfo") && $("#qinfo").open) || e.target.closest("input, textarea")) return;
  const R = Q.rounds[Q.i]; if (!R) return;
  if (/^[123]$/.test(e.key) && Q.picks.length <= Q.i) { e.preventDefault(); quizAnswer(R.opts[+e.key - 1]); }
  else if (e.key === " " && Q.mode !== "reverse") { e.preventDefault(); quizPlay(R.id, $(".quiz [data-play]")); }
  else if ((e.key === "Enter" || e.key === "ArrowRight") && Q.picks.length > Q.i && e.target.id !== "q-next") { e.preventDefault(); quizNext(); }
});

// ---------- feedback ----------
// The page can't send email itself (and mailto links don't open reliably for every artifact viewer), so the form
// composes the message: copy it, or open it in an email app where the browser allows. The address is assembled here
// rather than written into the HTML; the +1000x1000 tag and the subject prefix let a mail filter file it.
const FB_ADDR = ["ben.d.fulcher", "+1000x1000", "@", "gmail.com"].join("");
const FB_KINDS = [["fix", "A fix or correction"], ["series", "A new series or process"], ["question", "A question (for the FAQ)"], ["other", "Something else"]];
function feedbackCompose() {
  const kind = $("#fb-kind").value, sid = $("#fb-series").value.trim(), msg = $("#fb-msg").value.trim(), who = $("#fb-who").value.trim();
  const subject = `[1000×1000 feedback: ${kind}]${sid ? " " + sid : ""}`;
  const body = `${msg}\n\n—\nType: ${FB_KINDS.find(k => k[0] === kind)[1]}${sid ? `\nSeries: ${sid}` : ""}${who ? `\nReply to: ${who}` : ""}\nSent from the 1000×1000 website`;
  return { subject, body };
}
function openFeedback(seriesId = "") {
  let d = $("#fb");
  if (!d) {
    d = document.createElement("dialog"); d.id = "fb"; d.setAttribute("aria-labelledby", "fb-title"); document.body.appendChild(d);
    d.innerHTML = `<form class="fb" method="dialog">
      <div class="fb-head"><h2 id="fb-title">Send feedback</h2><button class="icon" type="button" id="fb-close" aria-label="Close">×</button></div>
      <p class="fb-lede">Spotted a problem, want a process added, or have a question? Suggestions and questions may be answered on the <a href="#/faq">FAQ</a> page.</p>
      <label><span>About</span><select id="fb-kind">${FB_KINDS.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
      <label><span>Series ID <span class="opt">(optional)</span></span><input id="fb-series" type="text" placeholder="e.g. S1000_FLOW_dysts-flow_020" spellcheck="false"></label>
      <label><span>Message</span><textarea id="fb-msg" rows="6" placeholder="What should change, or what would you like to see?"></textarea></label>
      <label><span>Your email or name <span class="opt">(optional, if you'd like a reply)</span></span><input id="fb-who" type="text"></label>
      <div class="fb-send">
        <p>To send, email this to <b class="fb-addr" id="fb-addr"></b></p>
        <div class="fb-act"><button class="btn primary" type="button" id="fb-copy">Copy message</button><a class="btn" id="fb-mail" href="#">Open in email app</a><span class="fb-note" id="fb-note" role="status"></span></div>
      </div>
      <textarea class="fb-fallback" id="fb-fallback" readonly hidden></textarea>
    </form>`;
    $("#fb-addr", d).textContent = FB_ADDR;
    d.addEventListener("click", e => { if (e.target === d || e.target.closest("#fb-close")) d.close(); });
    const refresh = () => { const { subject, body } = feedbackCompose(); $("#fb-mail").href = `mailto:${FB_ADDR}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; };
    d.addEventListener("input", refresh);
    $("#fb-copy", d).onclick = async () => {
      const { subject, body } = feedbackCompose(), t = `To: ${FB_ADDR}\nSubject: ${subject}\n\n${body}`;
      try { await navigator.clipboard.writeText(t); $("#fb-note").textContent = "Copied: paste it into an email to the address above."; }
      catch { const ta = $("#fb-fallback"); ta.hidden = false; ta.value = t; ta.select(); $("#fb-note").textContent = "Select the text below and copy it."; }
    };
    d.refresh = refresh;
  }
  $("#fb-series").value = seriesId; $("#fb-note").textContent = ""; $("#fb-fallback").hidden = true;
  d.refresh(); d.showModal(); $("#fb-msg").focus();
}
document.addEventListener("click", e => { const b = e.target.closest("[data-feedback]"); if (b) { e.preventDefault(); openFeedback(b.dataset.feedback || ""); } });

// ---------- FAQ ----------
// The questions live in faq.md (edit that file): "## " lines are questions, the paragraphs under them the answer.
// Inline Markdown: **bold**, *italic*, `code`, [text](url); maths as \( ... \) is typeset by KaTeX.
function mdInline(t) {
  const code = [];
  let h = esc(t).replace(/`([^`]+)`/g, (_, c) => `\u0000${code.push(c) - 1}\u0000`);
  h = h.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, txt, url) => /^(https?:|#|mailto:)/.test(url) ? `<a href="${url}"${url.startsWith("http") ? ' target="_blank" rel="noopener"' : ""}>${txt}</a>` : txt)
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[^*\w])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>");
  return h.replace(/\u0000(\d+)\u0000/g, (_, k) => `<code>${code[+k]}</code>`);
}
function parseFaq(md) {
  const out = [];
  for (const line of md.replace(/<!--[\s\S]*?-->/g, "").split("\n")) {
    if (line.startsWith("## ")) out.push({ q: line.slice(3).trim(), paras: [""] });
    else if (out.length) {
      const P = out[out.length - 1].paras;
      if (line.trim()) P[P.length - 1] += (P[P.length - 1] ? " " : "") + line.trim();
      else if (P[P.length - 1]) P.push("");
    }
  }
  return out.map(({ q, paras }) => ({ q, paras: paras.filter(Boolean) }));
}
async function viewFaq() {
  setNav("faq"); $("#view").dataset.cls = "";
  if (!S.faq) { try { S.faq = parseFaq(await (await fetch("faq.md", { cache: "no-cache" })).text()); } catch { S.faq = []; } }
  if (!location.hash.startsWith("#/faq")) return;
  $("#view").innerHTML = `<div class="prose faq">
    <h1>Questions and answers</h1>
    <p>Answers to questions about the collection, growing as people ask them. <a href="#" data-feedback="">Ask a question or send feedback</a>.</p>
    ${S.faq.map(({ q, paras }, k) => `<details class="faq-item"${k ? "" : " open"}><summary>${mdInline(q)}</summary>${paras.map(p => `<p>${mdInline(p)}</p>`).join("")}</details>`).join("")}
  </div>`;
  mathify($("#view"));
}

// ---------- router ----------
// Class bar under the header (wide screens; Explore page only): mascot + code per class, linking to its page.
function renderCbar(page, active = "") {
  const bar = $("#cbar");
  bar.hidden = page !== "explore";
  if (bar.hidden) return;
  bar.innerHTML = S.index.classes.map(c => `<a class="cp k-${c.code}" href="#/class/${c.short}" data-c="${c.code}" title="${esc(c.short)} · ${esc(c.title)}"${c.code === active ? ' aria-current="page"' : ""}>${c.icon ? `<span class="mascot sm" aria-hidden="true">${c.icon}</span>` : ""}<b>${c.short}</b></a>`).join("");
  bar.onclick = e => {
    const a = e.target.closest(".cp"); if (!a || page !== "map") return;
    e.preventDefault();
    mapState.cls = mapState.cls === a.dataset.c ? "" : a.dataset.c;
    if (mapState.cls) { mapState.tag = ""; const t = $("#mt"); if (t) t.value = ""; }
    syncLegend(); drawMap();
    bar.querySelectorAll(".cp").forEach(p => p.toggleAttribute("aria-current", p.dataset.c === mapState.cls));
  };
}

// ---------- search: classes, processes (families) and series, all in the browser ----------
let pendingFam = null, SEARCH = null;
const norm = t => String(t).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[-–—_/,().]+/g, " ").replace(/\s+/g, " ").trim();
// other names people search for
const ALIASES = { "Aizawa system": "Langford attractor", "Ornstein–Uhlenbeck process": "OU", "Hodgkin–Huxley neuron": "HH",
  "Lorenz system": "butterfly attractor", "Fractional Gaussian noise": "fGn fBm", "Hawkes process": "self exciting",
  "Mackey–Glass equation": "MG delay", "Chua circuit": "double scroll", "1/f noise": "pink noise flicker" };
function buildSearch() {
  const E = [];
  for (const c of S.index.classes) {
    E.push({ type: "Class", code: c.code, label: c.title[0].toUpperCase() + c.title.slice(1), sub: `${c.short} · ${c.n} series`,
             go: () => { location.hash = `#/class/${c.short}`; }, text: norm([c.title, c.short, c.name, c.mascot, c.blurb].join(" ")) });
    for (const f of c.families) {
      const recs = S.meta.filter(r => r.cls === c.code && r.family === f.key);
      E.push({ type: "Process", code: c.code, label: f.label, sub: `${c.short} · ${recs.length} series`,
               go: () => { pendingFam = f.key; location.hash === `#/class/${c.short}` ? viewClass(c.code) : (location.hash = `#/class/${c.short}`); },
               text: norm([f.label, f.key, ALIASES[f.label] || "", (f.labels || []).join(" "), f.card.description].join(" ")) });
    }
  }
  // series, grouped by name (eleven "AR(1) process" series are one result, pointing at their process)
  const byName = new Map();
  for (const r of S.meta) { const k = r.cls + "|" + r.name; if (!byName.has(k)) byName.set(k, []); byName.get(k).push(r); }
  for (const rs of byName.values()) {
    const r = rs[0], sys = Object.values(r.params).filter(v => typeof v === "string").join(" ");
    const fam = S.fam.get(`${r.cls}.${r.family}`);
    if (rs.length > 1 && fam && fam.label === r.name && rs.length === S.meta.filter(m => m.cls === r.cls && m.family === r.family).length) continue;  // same as its process
    const text = norm([r.name, ALIASES[r.name] || "", sys, (r.labels || []).join(" "), r.family, r.about || "", rs.map(x => x.id).join(" ")].join(" "));
    E.push(rs.length === 1
      ? { type: "Series", code: r.cls, label: r.name, sub: `${sc(r.cls)} · ${(r.labels || []).join(", ")}`, id: r.id, text,
          go: () => { const base = location.hash.startsWith("#/map") ? "" : `#/class/${sc(r.cls)}`; if (base && !location.hash.startsWith(base)) location.hash = `${base}/${r.id}`; else openSeries(r.id); } }
      : { type: "Series", code: r.cls, label: `${r.name} ×${rs.length}`, sub: `${sc(r.cls)} · ${(r.labels || []).join(", ")}`, text,
          go: () => { pendingFam = r.family; location.hash === `#/class/${sc(r.cls)}` ? viewClass(r.cls) : (location.hash = `#/class/${sc(r.cls)}`); } });
  }
  return E;
}
function searchFor(q) {
  const t = norm(q); if (!t) return [];
  const words = t.split(" ");
  const out = [];
  for (const e of SEARCH) {
    if (!words.every(w => e.text.includes(w))) continue;
    const l = norm(e.label);
    let s = l.startsWith(t) ? 100 : l.includes(t) ? 70 : words.every(w => l.includes(w)) ? 55 : 20;
    s += { Class: 6, Process: 4, Series: 0 }[e.type];
    out.push([s, e]);
  }
  return out.sort((a, b) => b[0] - a[0]).slice(0, 10).map(x => x[1]);
}
function wireSearch() {
  const q = $("#q"), box = $("#sr");
  let hits = [], sel = 0;
  const close = () => { box.hidden = true; q.setAttribute("aria-expanded", "false"); };
  const show = () => {
    SEARCH = SEARCH || buildSearch();
    hits = searchFor(q.value); sel = 0;
    if (!q.value.trim()) return close();
    box.innerHTML = hits.length ? hits.map((e, i) => `<div class="hit k-${e.code}" role="option" data-i="${i}" aria-selected="${i === sel}">
        ${S.cls.get(e.code).icon ? `<span class="mascot sm" aria-hidden="true">${S.cls.get(e.code).icon}</span>` : ""}
        <div><b>${esc(e.label)}</b><span>${esc(e.sub)}</span></div><i>${e.type}</i></div>`).join("")
      : `<div class="none">Nothing matches “${esc(q.value)}”.</div>`;
    box.hidden = false; q.setAttribute("aria-expanded", "true");
  };
  const pick = i => { const e = hits[i]; if (!e) return; close(); q.value = ""; q.blur(); e.go(); };
  const mark = () => box.querySelectorAll(".hit").forEach((h, i) => h.setAttribute("aria-selected", i === sel));
  q.addEventListener("input", show);
  q.addEventListener("focus", () => { if (q.value.trim()) show(); });
  q.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(hits.length - 1, sel + 1); mark(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); mark(); }
    else if (e.key === "Enter") { e.preventDefault(); pick(sel); }
    else if (e.key === "Escape") { close(); q.blur(); }
  });
  box.addEventListener("mousedown", e => { const h = e.target.closest(".hit"); if (h) { e.preventDefault(); pick(+h.dataset.i); } });
  q.addEventListener("blur", () => setTimeout(close, 120));
  addEventListener("keydown", e => {
    if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !$("#modal").open) { e.preventDefault(); q.focus(); }
  });
}

function route() {
  stopTicker(); setTimeout(discoSync);
  track(location.hash.replace(/^(#\/(class\/[^/]+|map))\/.+/, "$1"));
  document.body.classList.remove("landing");
  // links from before 2026-09-28 name series by class letter (S1000_G_...): translate them to the class code (S1000_FLOW_...)
  const h = location.hash.replace(/^#\/?/, "").split("/").map(p => p.replace(/^S1000_([A-N])_/, (_, c) => `S1000_${S.cls.get(c)?.short || c}_`));
  renderCbar(h[0] || "home", h[0] === "class" ? toCode(h[1]) : h[0] === "map" ? mapState.cls : "");
  if (h[0] !== "class" && h[0] !== "map" && $("#modal").open) { modalId = null; Audio.stop(); $("#modal").close(); }
  if (h[0] === "class") return viewClass(toCode(h[1]), h[2]);
  if (h[0] === "map") return viewMap(h[1]);
  if (h[0] === "about") return viewAbout();
  if (h[0] === "faq") return viewFaq();
  if (h[0] === "quiz") return viewQuiz();
  if (h[0] === "explore") { $("#view").dataset.cls = ""; return viewExplore(); }
  $("#view").dataset.cls = "";
  viewHome();
}
let rz;
addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => {
  if (location.hash.startsWith("#/map")) { drawMap(); const p = $("#mpanel"); if (p && p.dataset.id) renderPanel(p.dataset.id, true); }
  else if (location.hash.startsWith("#/explore")) document.querySelectorAll("canvas[data-prev]").forEach(cv => { const [c, id] = cv.dataset.prev.split("|"); trace(cv, S.cls.get(c).preview[id], { color: cink(cv) }); });
  else if (location.hash.startsWith("#/quiz")) quizRender();
  if (modalX && $("#modal").open) drawModal(modalX);
}, 150); });
wireModal();
wireSearch();
$("#view").addEventListener("click", e => { if ($("#view").dataset.cls) onClassClick(e); });
$("#view").addEventListener("keydown", e => { if (e.key === "Enter" && e.target.classList.contains("pane")) openSeries(e.target.dataset.id); });
boot().catch(e => { $("#view").innerHTML = `<p>Could not load data: ${esc(e.message)}. Run <code>s1000 site</code>, then serve with <code>python -m http.server -d site</code>.</p>`; });
