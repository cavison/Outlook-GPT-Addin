#!/usr/bin/env node
// Curtis' Manual builder: node build/build.js  ->  output/*.pdf (+ .html)
// Reads book.yaml, timeline/*.md, modules/**/*.md, diagrams/*.svg.
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { marked } = require('marked');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'output');
fs.mkdirSync(OUT, { recursive: true });
const book = yaml.load(fs.readFileSync(path.join(ROOT, 'book.yaml'), 'utf8'));
const warnings = [];

function walk(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : e.name.endsWith('.md') ? [path.join(dir, e.name)] : []);
}
function parse(file) {
  const raw = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) { warnings.push(`No front matter: ${file}`); return null; }
  let meta;
  try { meta = yaml.load(m[1]); } catch (e) { warnings.push(`Bad YAML in ${file}: ${e.message}`); return null; }
  return { meta, body: m[2], file };
}
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const slug = id => 'id-' + id.replace(/[^A-Za-z0-9]/g, '');

// ---- load content
const docs = {};
for (const f of [...walk(path.join(ROOT, 'timeline')), ...walk(path.join(ROOT, 'modules'))]) {
  const d = parse(f); if (!d || !d.meta.id) continue;
  if (docs[d.meta.id]) warnings.push(`Duplicate id ${d.meta.id}`);
  docs[d.meta.id] = d;
}
const titleOf = id => (docs[id] && docs[id].meta.title) || (book.modules || {})[id] || (book.chapter_titles || {})[id];
const catByPrefix = {};
for (const c of book.categories) catByPrefix[c.prefix] = c;
const catOf = id => catByPrefix[id.split('-')[0]];

const PHASE = { before: ['BEFORE', '#555'], '72h': ['72 HRS', '#c0392b'], wk: ['WEEKS 1–4', '#e67e22'], mo: ['MONTHS 2–3', '#2e7d32'], after: ['AFTER', '#1abc9c'] };

function xref(html) {
  return html.replace(/\[\[([A-Z]{1,2}-?\d{2})\]\]/g, (_, id) => {
    const t = titleOf(id);
    if (!t) { warnings.push(`Unknown reference [[${id}]]`); return `<b>${id}</b>`; }
    if (!docs[id]) warnings.push(`Reference to unwritten ${id}`);
    return `<a class="xref" href="#${slug(id)}"><b>${id}</b> ${esc(t)}</a>`;
  });
}
function md(s) { return xref(marked.parse(s || '')); }

function svgFor(name) {
  if (!name) return '';
  const p = path.join(ROOT, 'diagrams', name);
  if (!fs.existsSync(p)) { warnings.push(`Missing diagram ${name}`); return ''; }
  let s = fs.readFileSync(p, 'utf8').replace(/<\?xml[^>]*>/, '').replace(/<!DOCTYPE[^>]*>/i, '');
  // make responsive
  s = s.replace(/<svg\b([^>]*)>/, (m, a) => '<svg' + a.replace(/\s(width|height)="[^"]*"/g, '') + ' preserveAspectRatio="xMidYMid meet">');
  // namespace ids/markers so diagrams don't collide
  const pre = name.replace(/\W/g, '') + '_';
  s = s.replace(/\bid="([^"]+)"/g, `id="${pre}$1"`).replace(/url\(#([^)]+)\)/g, `url(#${pre}$1)`).replace(/href="#([^"]+)"/g, `href="#${pre}$1"`);
  return `<figure class="diagram">${s}</figure>`;
}

// split module body into labeled sections
function sections(body) {
  const parts = body.split(/^## +/m);
  const intro = parts.shift();
  const map = [];
  for (const p of parts) { const nl = p.indexOf('\n'); map.push([p.slice(0, nl).trim(), p.slice(nl + 1)]); }
  return { intro, map };
}

function renderModule(d) {
  const { meta } = d; const c = catOf(meta.id) || { color: '#333', name: '' };
  const { intro, map } = sections(d.body);
  const phases = (meta.phases || []).map(p => PHASE[p] ? `<span class="phase" style="border-color:${PHASE[p][1]};color:${PHASE[p][1]}">${PHASE[p][0]}</span>` : '').join('');
  let h = `<section class="module" id="${slug(meta.id)}" style="--cat:${c.color}">
<header class="mhead"><span class="mid">${esc(meta.id)}</span><h3>${esc(meta.title)}</h3></header>
<div class="mmeta">${phases}${meta.time ? `<span>⏱ ${esc(meta.time)}</span>` : ''}${meta.difficulty ? `<span>● ${esc(meta.difficulty)}</span>` : ''}${meta.verified ? `<span>✔ checked ${esc(meta.verified)}</span>` : ''}</div>
<div class="intro">${md(intro)}</div>${svgFor(meta.diagram)}`;
  for (const [name, txt] of map) {
    const k = name.toLowerCase();
    if (k.startsWith('caution')) h += `<div class="box caution"><div class="bt">⚠ CAUTION</div>${md(txt)}</div>`;
    else if (k.startsWith('field note')) h += `<div class="box tip"><div class="bt">💡 FIELD NOTE</div>${md(txt)}</div>`;
    else if (k.startsWith('sources')) h += `<div class="sources"><b>Sources:</b> ${md(txt).replace(/<\/?p>/g, '')}</div>`;
    else if (k.startsWith('see also')) h += `<div class="seealso"><b>See also:</b> ${md(txt).replace(/<\/?p>/g, '')}</div>`;
    else h += `<h4>${esc(name)}</h4><div class="sec sec-${k.replace(/\W+/g, '-')}">${md(txt)}</div>`;
  }
  if (meta.id === 'G-29') {
    const files = fs.existsSync(path.join(ROOT, 'images')) ? fs.readdirSync(path.join(ROOT, 'images')).filter(f => /^fish-.*\.(jpe?g|png|webp)$/i.test(f)).sort() : [];
    if (files.length) h += `<h4>Photo ID</h4><div class="fishgrid">${files.map(f => { const b = f.replace(/\.[^.]+$/, ''); const name = b.slice(5).replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); return `<figure><img src="${imgFor(b)}" alt="${esc(name)}"><figcaption>${esc(name)}</figcaption></figure>`; }).join('')}</div>`;
  }
  return h + '</section>';
}

function imgFor(base) {
  for (const ext of ['jpg', 'jpeg', 'png', 'webp']) {
    const p = path.join(ROOT, 'images', `${base}.${ext}`);
    if (fs.existsSync(p)) return 'data:image/' + (ext === 'jpg' ? 'jpeg' : ext) + ';base64,' + fs.readFileSync(p).toString('base64');
  }
  return null;
}
function renderChapter(d) {
  const { meta } = d; const op = imgFor(meta.id);
  return `<section class="chapter" id="${slug(meta.id)}">${op ? `<img class="opener" src="${op}" alt="">` : ''}<div class="chnum">Chapter ${parseInt(meta.id.slice(1), 10)}</div><h2>${esc(meta.title)}</h2>${md(d.body).replace(/<li>\[ \]/g, '<li class="check">☐')}</section>`;
}

// ---- assemble
const CARD_IDS = ['Q-01','Q-02','Q-03','Q-04','Q-05','Q-06','Q-07','Q-08','Q-09','Q-10','W-04','M-02','M-07','M-08','M-14','C-04','P-04','H-11'];
function buildCards() {
  const css = fs.readFileSync(path.join(__dirname, 'style.css'), 'utf8');
  return `<!doctype html><html><head><meta charset="utf-8"><title>Curtis' Manual — Cut-Out Cards</title><style>${css}</style></head><body class="phone cards">
<section class="howto"><h2>Curtis' Manual — Cut-Out Emergency Cards</h2><p>Print, cut, laminate or slip into sheet protectors. Keep one set by the flashlight, one in the car, one in the go-bag.</p></section>
${CARD_IDS.filter(id => docs[id]).map(id => renderModule(docs[id])).join('')}</body></html>`;
}
function buildHTML(variant) {
  let toc = '', body = '';
  // Book A
  toc += `<h3>Book A — The Timeline</h3>`;
  body += `<section class="bookdiv"><div class="bookdiv-inner"><div class="small">BOOK A</div><h1>The Timeline</h1><p>What is happening, what to decide, and which how-to modules to use — phase by phase.</p></div></section>`;
  for (const part of book.timeline) {
    toc += `<div class="tocpart">Part ${esc(part.part)}</div><ul>`;
    body += `<section class="partdiv"><h1>Part ${esc(part.part)}</h1></section>`;
    for (const id of part.chapters) {
      toc += `<li><a href="#${slug(id)}">${parseInt(id.slice(1), 10)}. ${esc(titleOf(id))}</a></li>`;
      if (docs[id]) body += renderChapter(docs[id]);
      else { warnings.push(`Missing chapter ${id}`); body += `<section class="chapter" id="${slug(id)}"><h2>${esc(titleOf(id))}</h2><p><i>Not yet written.</i></p></section>`; }
    }
    toc += '</ul>';
  }
  // Book B
  toc += `<h3>Book B — The Module Library</h3>`;
  body += `<section class="bookdiv"><div class="bookdiv-inner"><div class="small">BOOK B</div><h1>The Module Library</h1><p>Quick, step-by-step how-to guides. Each has a diagram, numbered steps, a caution and a field note. Find a module by its code, e.g. <b>W-04</b>.</p></div></section>`;
  for (const c of book.categories) {
    const ids = Object.keys(book.modules).filter(id => id.startsWith(c.prefix + '-'));
    toc += `<div class="tocpart" style="border-left:8px solid ${c.color};padding-left:6px">${c.prefix} — ${esc(c.name)}</div><ul class="cols">`;
    body += `<section class="catdiv" style="--cat:${c.color}"><div class="catletter">${c.prefix}</div><h1>${esc(c.name)}</h1><ul>${ids.map(id => `<li><a href="#${slug(id)}"><b>${id}</b> ${esc(titleOf(id))}</a></li>`).join('')}</ul></section>`;
    for (const id of ids) {
      toc += `<li><a href="#${slug(id)}"><b>${id}</b> ${esc(titleOf(id))}</a></li>`;
      if (docs[id]) body += renderModule(docs[id]);
      else warnings.push(`Missing module ${id}`);
    }
    toc += '</ul>';
  }
  // ---- topic index
  const STOP = new Set('the and for with from your when what how without into that this than are can not don\'t own one two you its out off use get keep make safely safe right new run set build using'.split(' '));
  const idx = {};
  for (const id of Object.keys(book.modules)) {
    const d = docs[id]; if (!d) continue;
    const terms = new Set([...(d.meta.keywords || []).map(String), ...titleOf(id).split(/[^A-Za-z0-9'-]+/)]);
    for (let t of terms) { t = t.trim().toLowerCase().replace(/^'|'$/g, ''); if (t.length < 4 || STOP.has(t) || /^\d/.test(t)) continue; (idx[t] = idx[t] || new Set()).add(id); }
  }
  const terms = Object.keys(idx).sort();
  toc += `<h3><a href="#topic-index">Topic Index</a></h3>`;
  body += `<section class="index" id="topic-index"><h2>Topic Index</h2><div class="idxcols">${terms.map(t => `<div class="ie"><b>${esc(t)}</b> ${[...idx[t]].sort().map(id => `<a href="#${slug(id)}">${id}</a>`).join(', ')}</div>`).join('')}</div></section>`;
  const css = fs.readFileSync(path.join(__dirname, 'style.css'), 'utf8');
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(book.title)}</title><style>${css}</style></head>
<body class="${variant}">
<section class="cover"><div class="cover-band"></div><div class="cover-inner">
<div class="cover-kicker">WHEN IT HITS THE FAN — AND THE FAN WON'T SPIN</div>
<h1>${esc(book.title)}</h1><p class="sub">${esc(book.subtitle)}</p>
<div class="cover-art">${svgFor('cover.svg')}</div>
<p class="ed">${esc(book.edition)}</p></div></section>
<section class="howto"><h2>How to use this manual</h2>
<p><b>Book A — The Timeline</b> follows an outage from preparation to recovery. Read it before anything happens; during an outage, open the part for where you are.</p>
<p><b>Book B — The Module Library</b> holds short how-to guides. Every module has a code (W = Water, H = Heat, M = Medical…). Each one gives: what it's for, what you need, numbered steps matched to a diagram, a <span style="color:#c0392b"><b>⚠ Caution</b></span> and a <span style="color:#2e7d32"><b>💡 Field note</b></span>.</p>
<p>Phase tags tell you when a module matters: <span class="phase" style="color:#555;border-color:#555">BEFORE</span> <span class="phase" style="color:#c0392b;border-color:#c0392b">72 HRS</span> <span class="phase" style="color:#e67e22;border-color:#e67e22">WEEKS 1–4</span> <span class="phase" style="color:#2e7d32;border-color:#2e7d32">MONTHS 2–3</span> <span class="phase" style="color:#1abc9c;border-color:#1abc9c">AFTER</span></p>
<p><b>In an emergency right now, go to the red Quick Start Cards (Q-01 to Q-10).</b></p>
<div class="box caution"><div class="bt">⚠ IMPORTANT</div><p>This manual is general information for preparedness, not medical, legal or professional advice. Take a first-aid / Stop the Bleed class, follow local authorities and current official guidance, and check Michigan DNR, FCC and local rules before fishing, trapping, hunting, burning or transmitting by radio. Verify every phone number and frequency before you need it.</p></div>
</section>
<section class="toc"><h2>Contents</h2>${toc}</section>
${body}
</body></html>`;
}

(async () => {
  const variants = [
    { name: 'print', file: "Curtis-Manual-PRINT-8.5x11.pdf", pdf: { format: 'Letter', margin: { top: '0.6in', bottom: '0.7in', left: '0.7in', right: '0.7in' } } },
    { name: 'phone', file: "Curtis-Manual-PHONE.pdf", pdf: { width: '4.25in', height: '7.5in', margin: { top: '0.3in', bottom: '0.45in', left: '0.25in', right: '0.25in' } } },
  ];
  variants.push({ name: 'cards', file: 'Curtis-Manual-CARDS-half-letter.pdf', html: buildCards, pdf: { width: '5.5in', height: '8.5in', margin: { top: '0.3in', bottom: '0.4in', left: '0.3in', right: '0.3in' } } });
  const only = process.argv[2];
  const browser = await chromium.launch();
  for (const v of variants) {
    if (only && only !== v.name) continue;
    const html = v.html ? v.html() : buildHTML(v.name);
    const hp = path.join(OUT, `book-${v.name}.html`);
    fs.writeFileSync(hp, html);
    const page = await browser.newPage();
    await page.goto('file://' + hp, { waitUntil: 'load' });
    await page.pdf({ path: path.join(OUT, v.file), printBackground: true, displayHeaderFooter: true,
      headerTemplate: '<div></div>',
      footerTemplate: `<div style="width:100%;font-size:${v.name === 'phone' ? 7 : 8}px;font-family:Arial;color:#666;padding:0 0.5in;display:flex;justify-content:space-between"><span>Curtis' Manual</span><span class="pageNumber"></span></div>`,
      ...v.pdf });
    await page.close();
    console.log('Wrote', v.file);
  }
  await browser.close();
  const uniq = [...new Set(warnings)];
  fs.writeFileSync(path.join(OUT, 'build-warnings.txt'), uniq.join('\n') + '\n');
  console.log(`${Object.keys(docs).length} docs, ${uniq.length} warnings (see output/build-warnings.txt)`);
})();
