<script>
/* ---------- config ---------- */
const ROUNDS = 16;
const SLOTS = [["QB","QB"],["RB","RB1"],["RB","RB2"],["WR","WR1"],["WR","WR2"],["TE","TE"],
               ["FLEX","FLEX"],["K","K"],["DST","D/ST"],
               ["BN","Bench 1"],["BN","Bench 2"],["BN","Bench 3"],["BN","Bench 4"],
               ["BN","Bench 5"],["BN","Bench 6"],["BN","Bench 7"]];
const FLEXOK = {RB:1,WR:1,TE:1};
const POSNAME = {QB:"Quarterback",RB:"Running back",WR:"Wide receiver",TE:"Tight end",K:"Kicker",DST:"Defense"};

/* ---------- state ---------- */
let teams = 12, slot = 1;
let taken = new Map();          // rank -> "mine" | "gone"
let history = [];               // [rank, ...] in order
let filter = "ALL", query = "";

const $ = id => document.getElementById(id);
const byRank = new Map(PLAYERS.map(p => [p.r, p]));

function save(){ try{ localStorage.setItem("otc26", JSON.stringify(
  {teams, slot, h: history, t:[...taken]})); }catch(e){} }
function load(){ try{
  const s = JSON.parse(localStorage.getItem("otc26")||"null"); if(!s) return;
  teams = s.teams||12; slot = s.slot||1; history = s.h||[]; taken = new Map(s.t||[]);
}catch(e){} }

/* ---------- draft math ---------- */
const pickNum = () => taken.size + 1;
const roundOf = n => Math.min(ROUNDS, Math.ceil(n / teams));
function myPicks(){
  const out=[]; for(let r=1;r<=ROUNDS;r++){
    out.push((r-1)*teams + (r%2 ? slot : teams - slot + 1));
  } return out;
}
const nextMine = () => myPicks().find(p => p >= pickNum());
const isMyTurn = () => myPicks().includes(pickNum());

/* ---------- roster ---------- */
function buildRoster(mine){
  const filled = SLOTS.map(([t,l]) => ({type:t,label:l,player:null}));
  const put = (p, types) => {
    for(const s of filled){ if(!s.player && types.includes(s.type)){ s.player=p; return true; } }
    return false;
  };
  for(const p of mine){
    if(!put(p,[p.p]) && !(FLEXOK[p.p] && put(p,["FLEX"]))) put(p,["BN"]);
  }
  return filled;
}
const openTypes = roster => new Set(roster.filter(s=>!s.player).map(s=>s.type));

/* ---------- the engine ---------- */
function availableAt(pick, exclude){
  return PLAYERS.filter(p => !taken.has(p.r) && !(exclude&&exclude.has(p.r)) && p.r >= pick);
}
function poolNow(exclude){
  return PLAYERS.filter(p => !taken.has(p.r) && !(exclude&&exclude.has(p.r)));
}

// how much worse your best option gets if you wait one full turn
function dropoff(pos, pool, futurePick){
  const at = pool.filter(p => p.p===pos);
  if(!at.length) return {now:null, later:null, gap:0};
  const now = at[0];
  const later = at.find(p => p.r >= futurePick) || null;
  return {now, later, gap: later ? later.r - now.r : 260 - now.r};
}

function weight(pos, open, round, counts, mustFill, soleFor){
  if(mustFill) return soleFor.has(pos) ? 10 : 3;   // last picks: fill the empty starting slots
  if(pos==="K"||pos==="DST") return 0;             // never before the must-fill window
  if(pos==="QB"){
    if(counts.QB>=2) return 0;
    if(counts.QB>=1) return round>=13 ? .25 : 0;
    return round>=10 ? 2.2 : 1;
  }
  if(pos==="TE"){
    if(counts.TE>=2) return 0;
    if(counts.TE>=1) return .18;
    return open.has("TE") ? (round>=10 ? 2.2 : 1) : .18;
  }
  if(open.has(pos)) return round>=ROUNDS-4 ? 1.5 : 1;
  if(open.has("FLEX")) return .75;
  return .45;
}

function evaluate(round, roster, pool, futurePick, picksLeft, pick){
  const open = openTypes(roster);
  const counts = {};
  roster.forEach(s => { if(s.player) counts[s.player.p] = (counts[s.player.p]||0)+1; });

  // once you have exactly as many picks left as empty starting slots, you are out of choices
  const need = roster.filter(s => !s.player && s.type !== "BN");
  const mustFill = picksLeft <= need.length;
  const canFill = new Set(), soleFor = new Set();
  need.forEach(s => {
    if(s.type==="FLEX"){ ["RB","WR","TE"].forEach(p => canFill.add(p)); }
    else { canFill.add(s.type); soleFor.add(s.type); }
  });

  let rows = ["RB","WR","TE","QB","K","DST"].map(pos => {
    const d = dropoff(pos, pool, futurePick);
    const w = weight(pos, open, round, counts, mustFill, soleFor);
    if(!d.now || w<=0) return null;
    // surplus: how far the best man left has fallen past this pick, in rounds
    const surplus = (pick - d.now.r) / teams;
    const v = Math.max(Math.log(1 + Math.max(d.gap,0)) + surplus, .15);
    return {pos, ...d, w, mustFill, score: w * v};
  }).filter(Boolean);

  if(mustFill) rows = rows.filter(r => canFill.has(r.pos));
  rows.sort((a,b) => b.score - a.score);
  return rows;
}

// forward-simulate the rest of the draft to build the round strip
function projectPlan(){
  const mine = history.filter(r => taken.get(r)==="mine").map(r => byRank.get(r));
  const done = {};
  const picks = myPicks();
  mine.forEach((p,i) => { done[roundOf(picks[i])] = p.p; });

  const plan = {};
  const used = new Set();
  let roster = buildRoster(mine.slice());
  const simMine = mine.slice();
  for(const pk of picks){
    const r = roundOf(pk);
    if(done[r]){ plan[r] = {pos:done[r], done:true}; continue; }
    const pool = availableAt(pk, used);
    const left = picks.filter(x => x >= pk).length;
    const rows = evaluate(r, roster, pool, pk + teams*2, left, pk);
    if(!rows.length){ plan[r] = {pos:"—", done:false}; continue; }
    plan[r] = {pos: rows[0].pos, done:false};
    used.add(rows[0].now.r);
    simMine.push(rows[0].now);
    roster = buildRoster(simMine.slice());
  }
  return plan;
}

/* ---------- alerts ---------- */
function makeAlerts(rows, roster, round, pool){
  const out=[]; const open = openTypes(roster);
  const nm = nextMine(), after = myPicks().find(p => p > nm);
  if(round >= ROUNDS-1 && (open.has("K")||open.has("DST")))
    out.push(["stop", `<b>Last calls.</b> You still need ${[...open].filter(t=>t==="K"||t==="DST").join(" and ")}. Take them now — this is the only reason these rounds exist.`]);
  if(round >= 11 && open.has("QB"))
    out.push(["stop", `<b>You still have no quarterback.</b> Round ${round} of ${ROUNDS}. Take one in the next pick or two.`]);
  if(round >= 11 && open.has("TE"))
    out.push(["stop", `<b>You still have no tight end.</b> Don't leave this to the last round.`]);
  const top = rows[0];
  if(top && after){
    const before = pool.filter(p => p.p===top.pos && p.r < after).length;
    if(before && before <= 3)
      out.push(["warn", `<b>Only ${before} ${top.pos}${before>1?"s":""} left</b> who are likely to survive to your next pick (#${after}). If you want one, this is the turn.`]);
  }
  if(top && top.gap >= 45)
    out.push(["go", `<b>Big gap at ${top.pos}.</b> The best one available is ${top.gap} spots better than what is likely to be there next time you pick. That gap is the whole reason to go ${top.pos} now.`]);
  if(!out.length && top)
    out.push(["go", `<b>No emergencies.</b> Take the best ${top.pos} on the board and keep your roster balanced.`]);
  return out;
}

/* ---------- render ---------- */
function render(){
  const pk = pickNum(), round = roundOf(pk), mine = history.filter(r=>taken.get(r)==="mine").map(r=>byRank.get(r));
  const roster = buildRoster(mine), pool = poolNow();
  const nm = nextMine(), after = myPicks().find(p => p > nm);
  const left = myPicks().filter(x => x >= pk).length;
  const advRound = roundOf(nm || pk);
  const rows = evaluate(advRound, roster, pool, (after || nm + teams*2), left, nm || pk);

  $("pickno").textContent = `Pick ${pk} · Round ${round}`;
  const turn = isMyTurn();
  $("yourturn").textContent = turn ? "You are up" : (nm ? `You pick at #${nm}` : "Draft complete");
  $("yourturn").className = "pickno" + (turn ? " live" : "");

  // the call
  const top = rows[0];
  if(top){
    $("callpos").textContent = POSNAME[top.pos];
    $("callchip").innerHTML = `<span class="chip ${top.pos}">${top.pos}</span>`;
    $("callmeta").textContent = turn ? "you are on the clock" : `planning ahead for pick #${nm}`;
    const alt = rows[1];
    $("callwhy").innerHTML = top.gap >= 260 - (top.now?top.now.r:0)
      ? `Take the best ${top.pos} left — the position is thin enough that waiting costs you real value.`
      : `Waiting a full turn costs you about <strong>${top.gap} spots</strong> of quality at ${top.pos}` +
        (alt ? `, versus ${alt.gap} at ${alt.pos}. That is why ${top.pos} is the call.` : `. That is why ${top.pos} is the call.`);
    const cands = [];
    pool.filter(p=>p.p===top.pos).slice(0,2).forEach(p=>cands.push(p));
    if(alt) { const a = pool.find(p=>p.p===alt.pos); if(a) cands.push(a); }
    $("callpicks").innerHTML = cands.map((p,i)=>`
      <div class="pick${i===0?" top":""}">
        <span class="chip ${p.p}">${p.k}</span>
        <span class="nm clickable" data-open="${p.r}" tabindex="0" role="button">${esc(p.n)}<small>${esc(p.t)} · overall ${p.r}</small></span>
        <button class="mine" data-mine="${p.r}" type="button">Mine</button>
        <button class="gone" data-gone="${p.r}" type="button">Gone</button>
      </div>`).join("");
  } else {
    $("callpos").textContent = "Done";
    $("callchip").innerHTML=""; $("callmeta").textContent="";
    $("callwhy").textContent = "Your roster is full. Good luck.";
    $("callpicks").innerHTML = "";
  }
  $("alerts").innerHTML = makeAlerts(rows, roster, advRound, pool)
    .map(([k,html])=>`<div class="alert ${k}">${html}</div>`).join("");

  // round plan
  const plan = projectPlan();
  $("rounds").innerHTML = Array.from({length:ROUNDS},(_,i)=>i+1).map(r=>{
    const e = plan[r] || {pos:"—"};
    const cls = e.done ? "done" : (r===round ? "now" : "");
    return `<div class="rd ${cls}"><span class="n">R${r}</span><span class="p">${e.pos}</span></div>`;
  }).join("");
  $("plankey").innerHTML = `Your picks this draft: <span class="mono">${myPicks().map(p=>"#"+p).join("  ")}</span>`;

  // roster
  const openT = openTypes(roster);
  $("roster").innerHTML = roster.map(s=>{
    const urgent = !s.player && (s.type==="K"||s.type==="DST") && round>=ROUNDS-1;
    return `<div class="slot ${s.player?"filled":""} ${urgent?"urgent":""}">
      <span class="lbl">${s.label}</span>
      <span class="val${s.player?" clickable":""}" ${s.player?`data-open="${s.player.r}" tabindex="0" role="button"`:""}>${s.player?esc(s.player.n)+`<small>${s.player.k} · ${esc(s.player.t)}</small>`:"&nbsp;"}</span></div>`;
  }).join("");
  $("rostermeta").textContent = `${mine.length} of ${ROUNDS} picked`;

  // pool
  const list = pool.filter(p => (filter==="ALL"||p.p===filter) &&
    (!query || p.n.toLowerCase().includes(query) || p.t.toLowerCase().includes(query))).slice(0,120);
  let html = "", shown = 0;
  list.forEach((p,i)=>{
    const prev = list[i-1];
    if(prev && filter!=="ALL" && p.r - prev.r >= 40)
      html += `<div class="cliff">↓ tier drop — ${p.r - prev.r} spots</div>`;
    html += `<div class="prow">
      <span class="rk">${p.r}</span>
      <span class="nm clickable" data-open="${p.r}" tabindex="0" role="button">${esc(p.n)}<small>${esc(p.t)}</small></span>
      <span class="chip ${p.p}">${p.k}</span>
      <button class="mine" data-mine="${p.r}" type="button">Mine</button>
      <button class="gone" data-gone="${p.r}" type="button">Gone</button></div>`;
    shown++;
  });
  $("pool").innerHTML = shown ? html : `<div class="empty">Nobody left matching that.</div>`;
  $("poolmeta").textContent = `${pool.length} left on the board`;
  save(); if(!FS.file) stamp(); scheduleWrite();
}

function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }


/* ---------- player detail (read-only: never touches draft state) ---------- */
let lastFocus = null;
const CONF = {High:"Sources agree on this range", Medium:"Role-based inference", Low:"Deep-league guess — verify the team"};
const SLEEP = {"post-hype":"Post-hype","repriced":"Role changed, price didn't","year-two":"Second-year leap",
               "runway":"Somebody else's injury","buried":"Buried by a bigger name","free":"Free late"};

function openCard(rank){
  const p = byRank.get(rank); if(!p) return;
  lastFocus = document.activeElement;
  const pk = pickNum(), nm = nextMine(), state = taken.get(rank);
  const atPos = PLAYERS.filter(x => x.p===p.p && !taken.has(x.r) && x.r > p.r).slice(0,3);
  const lasts = nm ? p.r >= nm : true;

  const tags = [];
  if(state) tags.push(`<span class="tag solid">${state==="mine"?"On your roster":"Already drafted"}</span>`);
  if(p.sl) tags.push(`<span class="tag">Sleeper · ${esc(SLEEP[p.sl]||p.sl)}</span>`);
  if(p.ru==="dual") tags.push(`<span class="tag solid">Dual-threat QB</span>`);
  if(p.ru==="run") tags.push(`<span class="tag">Runs, thin passer</span>`);
  if(p.cf==="Low") tags.push(`<span class="tag warn">Verify before drafting</span>`);

  let bodyHtml = "";
  if(p.no) bodyHtml += `<h4>Why he is here</h4><p>${esc(p.no)}</p>`;
  if(p.ca) bodyHtml += `<h4>The sleeper case${p.co?` · ${esc(p.co)}`:""}</h4><p>${esc(p.ca)}</p>`;
  if(p.rs) bodyHtml += `<h4>Rushing, 2025</h4><p>${esc(p.rs)}</p>`;
  if(!bodyHtml) bodyHtml = `<h4>Why he is here</h4><p>No individual write-up for this one — he is on the board on
    rank and role. At overall ${p.r} he is a ${p.cf==="Low"?"deep-league flier":"depth piece"}, so treat the
    numbers above as the whole case.</p>`;

  bodyHtml += `<h4>If you pass, the next ${p.p}s are</h4><div class="nextup">` +
    (atPos.length ? atPos.map(x =>
      `<div class="n"><span>${esc(x.n)} <span class="g">${x.k} · ${esc(x.t)}</span></span>
       <span class="g">${x.r - p.r} spots later</span></div>`).join("")
      : `<div class="n"><span>Nobody left at this position.</span><span class="g">—</span></div>`) + `</div>`;

  $("sheet").innerHTML = `
    <div class="top">
      <div class="who"><h3 id="sheetname">${esc(p.n)}</h3>
        <span class="sub">${p.k} · ${esc(p.t)} · overall ${p.r}</span></div>
      <span class="chip ${p.p}">${p.p}</span>
      <button class="x" id="sheetclose" type="button" aria-label="Close">✕</button>
    </div>
    ${tags.length?`<div class="tags">${tags.join("")}</div>`:""}
    <dl class="facts">
      <div><dt>Overall</dt><dd>${p.r}</dd></div>
      <div><dt>Position</dt><dd>${p.k}</dd></div>
      <div><dt>Target</dt><dd>${esc(p.rd||"—")}</dd></div>
      <div><dt>Confidence</dt><dd>${esc(p.cf||"—")}</dd></div>
    </dl>
    <div class="body">
      <h4>Will he last?</h4>
      <p>${nm ? (lasts
          ? `Your next pick is <strong>#${nm}</strong> and he sits at overall ${p.r}. Players ranked below your
             pick number usually survive, so there is a fair chance he is still here — you can take someone
             scarcer now.`
          : `Your next pick is <strong>#${nm}</strong> and he sits at overall ${p.r}, which is ${nm - p.r}
             spots ahead of it. If you want him, it has to be this turn.`)
        : `The draft is over.`}</p>
      <p style="margin-top:8px;color:var(--muted);font-size:13px">${esc(CONF[p.cf]||"")}.</p>
      ${bodyHtml}
    </div>
    <div class="act">
      <button class="mine" data-mine="${p.r}" type="button">Mine</button>
      <button class="gone" data-gone="${p.r}" type="button">Someone took him</button>
      <button class="ghost" data-close="1" type="button">Close</button>
    </div>`;
  $("scrim").classList.add("open");
  const c = $("sheetclose"); if(c) c.focus();
}
function closeCard(){
  $("scrim").classList.remove("open");
  $("sheet").innerHTML = "";
  if(lastFocus && lastFocus.focus) lastFocus.focus();
}


/* ---------- storage: a real folder on this computer ---------- */
const FILENAME = "fantasy-draft-2026.json";
const FS = { can: typeof window.showDirectoryPicker === "function", dir:null, file:null };
let writeTimer = null;

function idb(){
  return new Promise((res, rej) => {
    let rq; try { rq = indexedDB.open("otc-handles", 1); } catch(e){ return rej(e); }
    rq.onupgradeneeded = () => rq.result.createObjectStore("h");
    rq.onsuccess = () => res(rq.result); rq.onerror = () => rej(rq.error);
  });
}
async function keep(handle){
  try { const db = await idb();
    await new Promise((res,rej)=>{ const t=db.transaction("h","readwrite");
      t.objectStore("h").put(handle,"dir"); t.oncomplete=res; t.onerror=()=>rej(t.error); });
  } catch(e){ /* file:// often blocks IndexedDB — folder just won't auto-reconnect */ }
}
async function recall(){
  try { const db = await idb();
    return await new Promise((res,rej)=>{ const t=db.transaction("h","readonly");
      const g=t.objectStore("h").get("dir"); g.onsuccess=()=>res(g.result||null); g.onerror=()=>rej(g.error); });
  } catch(e){ return null; }
}

function payload(){ return JSON.stringify({v:1, saved:new Date().toISOString(), teams, slot,
  h:history, t:[...taken],
  roster: history.filter(r=>taken.get(r)==="mine").map(r=>{const p=byRank.get(r);
    return p?{rank:p.r, name:p.n, pos:p.k, team:p.t}:null;}).filter(Boolean)}, null, 1); }

async function attach(dirHandle){
  FS.dir = dirHandle;
  FS.file = await dirHandle.getFileHandle(FILENAME, {create:true});
  await keep(dirHandle);
  mode(`Saving to <strong>${esc(dirHandle.name)}/${FILENAME}</strong>`, true);
}
async function writeOut(){
  if(!FS.file) return;
  try {
    const w = await FS.file.createWritable();
    await w.write(payload()); await w.close();
    stamp("Saved to " + FS.dir.name);
  } catch(e){ mode("Folder write failed — falling back to this browser", false); FS.file=null; }
}
function scheduleWrite(){ if(!FS.file) return; clearTimeout(writeTimer); writeTimer=setTimeout(writeOut, 400); }

async function loadFrom(fileHandle){
  const f = await fileHandle.getFile();
  const txt = await f.text(); if(!txt.trim()) return false;
  return adopt(JSON.parse(txt));
}
function adopt(s){
  if(!s || !Array.isArray(s.h)) return false;
  teams = s.teams||12; slot = s.slot||1; history = s.h; taken = new Map(s.t||[]);
  $("teams").value = teams; buildSlots(); render(); return true;
}

function mode(html, connected){
  $("storemode").innerHTML = html;
  $("storedot").style.background = connected ? "var(--go)" : "var(--warn)";
  $("disconnect").hidden = !connected;
}
function stamp(what){
  const d = new Date();
  $("savestat").textContent = (what||"Saved in this browser") + " · " +
    d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
}

async function chooseFolder(){
  try {
    const dir = await window.showDirectoryPicker({mode:"readwrite", id:"otc26"});
    if(await dir.requestPermission({mode:"readwrite"}) !== "granted") return;
    const fh = await dir.getFileHandle(FILENAME, {create:true});
    const existing = await fh.getFile();
    if(existing.size > 2 && confirm(`${FILENAME} already exists in that folder.\n\nOK = load the draft that is in it.\nCancel = overwrite it with what is on screen.`)){
      await attach(dir); await loadFrom(fh); return;
    }
    await attach(dir); await writeOut(); render();
  } catch(e){ if(e && e.name !== "AbortError") mode("Could not open that folder", false); }
}

async function reconnect(){
  const dir = await recall(); if(!dir) return false;
  let p = await dir.queryPermission({mode:"readwrite"});
  if(p !== "granted") p = await dir.requestPermission({mode:"readwrite"});
  if(p !== "granted") return false;
  await attach(dir);
  const fh = await dir.getFileHandle(FILENAME, {create:true});
  await loadFrom(fh);
  return true;
}

/* portable fallbacks — these work in every browser, including from a file:// page */
function saveCopy(){
  const blob = new Blob([payload()], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = FILENAME;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href), 4000);
}
function openCopy(){
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json";
  inp.onchange = () => { const f = inp.files[0]; if(!f) return;
    const fr = new FileReader();
    fr.onload = () => { try { if(!adopt(JSON.parse(fr.result))) throw 0; }
      catch(e){ alert("That file did not read as a saved draft."); } };
    fr.readAsText(f); };
  inp.click();
}
/* ---------- events ---------- */
document.addEventListener("click", e=>{
  if(e.target.closest("[data-close]") || e.target.id==="sheetclose"){ closeCard(); return; }
  if(e.target === $("scrim")){ closeCard(); return; }
  const m = e.target.closest("[data-mine]"), g = e.target.closest("[data-gone]");
  const r = m ? +m.dataset.mine : g ? +g.dataset.gone : null;
  if(r!==null){
    taken.set(r, m ? "mine" : "gone"); history.push(r);
    if($("scrim").classList.contains("open")) closeCard();
    $("find").value = ""; query = ""; render();
    return;
  }
  const o = e.target.closest("[data-open]");
  if(o) openCard(+o.dataset.open);   // read-only: no state change, nothing saved
});
document.addEventListener("keydown", e=>{
  if(e.key==="Escape" && $("scrim").classList.contains("open")){ closeCard(); return; }
  if((e.key==="Enter"||e.key===" ")){
    const o = e.target.closest && e.target.closest("[data-open]");
    if(o){ e.preventDefault(); openCard(+o.dataset.open); }
  }
});
$("undo").onclick = ()=>{ const r = history.pop(); if(r!=null) taken.delete(r); render(); };
$("reset").onclick = ()=>{ if(confirm("Clear this draft and start over?")){ taken.clear(); history=[]; render(); } };
$("find").oninput = e => { query = e.target.value.trim().toLowerCase(); render(); };
$("teams").onchange = e => { teams = +e.target.value; buildSlots(); render(); };
$("pickfolder").onclick = chooseFolder;
$("disconnect").onclick = ()=>{ FS.dir=null; FS.file=null;
  mode("This browser only — pick a folder to save to disk", false); stamp(); };
$("savecopy").onclick = saveCopy;
$("opencopy").onclick = openCopy;
function buildSlots(){
  const sel = $("slot"); const keep = slot;
  sel.innerHTML = Array.from({length:teams},(_,i)=>`<option value="${i+1}">${i+1}</option>`).join("");
  slot = Math.min(keep, teams); sel.value = slot;
  sel.onchange = e => { slot = +e.target.value; render(); };
}
["ALL","QB","RB","WR","TE","K","DST"].forEach(p=>{
  const b=document.createElement("button"); b.className="pt"; b.type="button";
  b.textContent = p==="ALL"?"All":p; b.setAttribute("aria-pressed", p==="ALL");
  b.onclick=()=>{ filter=p; [...$("postabs").children].forEach(c=>c.setAttribute("aria-pressed",c===b)); render(); };
  $("postabs").appendChild(b);
});

load(); $("teams").value = teams; buildSlots(); render();
if(!FS.can){
  mode("This browser does not support folder saving — use <em>Save a copy</em> and <em>Open a draft</em>", false);
  $("pickfolder").disabled = true; $("pickfolder").title = "Needs Chrome, Edge or Opera on desktop";
} else {
  mode("This browser only — pick a folder to save to disk", false);
  recall().then(async dir => {
    if(!dir) return;
    if(await dir.queryPermission({mode:"readwrite"}) === "granted"){ await reconnect(); }
    else { mode(`Folder <strong>${esc(dir.name)}</strong> remembered — click Reconnect`, false);
           $("pickfolder").textContent = "Reconnect folder"; $("pickfolder").onclick = async ()=>{
             if(!await reconnect()) chooseFolder(); }; }
  }).catch(()=>{});
}
</script>
