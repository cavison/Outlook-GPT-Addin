# -*- coding: utf-8 -*-
"""Rebuild drills.html: per-operator chapters, a source panel on every card,
and a browsable dossier mode. Surgical patch of the existing file so the CSS
and game engine are untouched except where listed."""
import os, io, re, json, sys

SP = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(SP, 'art', 'drills.html')
h = io.open(P, encoding='utf-8').read()
orig_len = len(h)

def must(cond, msg):
    if not cond:
        print('FAIL:', msg); sys.exit(1)

def rep1(old, new, label):
    global h
    must(h.count(old) == 1, 'expected exactly 1 occurrence of ' + label + ' (found %d)' % h.count(old))
    h = h.replace(old, new)

read = lambda n: io.open(os.path.join(SP, n), encoding='utf-8').read()

# ---------- 1. CSS ----------
rep1('</style>', read('ui_css.txt') + '</style>', 'style close')

# ---------- 2. HUD: dossier-mode button ----------
rep1('      <button class="icon-btn" id="sound"',
     '      <button class="icon-btn" id="mode" type="button" title="Browse the operator dossiers">DOSSIERS</button>\n'
     '      <button class="icon-btn" id="sound"', 'sound button')

# ---------- 3. operator bar under the chapter progress ----------
rep1('<div id="stage"></div>',
     '<div class="opbar" id="opbar"></div>\n  <div id="stage"></div>', 'stage div')

# ---------- 4. lift the old single operator chapter out of CH ----------
i0 = h.index('{name:"Operator Playbooks"')
i1 = h.index('{name:"Money"')
old_op_block = h[i0:i1]
must(old_op_block.rstrip().endswith(']},'), 'operator block ends cleanly')
h = h[:i0] + h[i1:]

# ---------- 5. add the "three brackets" card to The Shape ----------
anchor = ('  say:"Maintenance is the floor. Every operator does it and nobody itemises it."}\n]},')
bracket = ('  say:"Maintenance is the floor. Every operator does it and nobody itemises it."},\n'
 ' {n:"Three brackets",t:"hold the whole market, and we have to pick one",'
 'c:"Five Star is the bundled end: weekly housekeeping with flat linen in the fee at all five of their properties. '
 'Trilogy is the \\u00e0 la carte end: bi-weekly housekeeping and then a menu, and no transportation at any of eight. '
 'Arrow\'s Vitalia is amenity-led and lists almost no services at all across seven. Those three bracket everything else.",\n'
 '  q:"Which three operators bracket the market?",'
 'o:["Five Star, Trilogy and Arrow","Capri, Traditions and ASC","Only the CCRCs","Life Care Services alone"],a:0,\n'
 '  w:"Bundled, \\u00e0 la carte, amenity-led. Twenty communities between Trilogy, Five Star and Arrow list no transportation at all.",\n'
 '  say:"Three operators bracket this market. Five Star is bundled, Trilogy is \\u00e0 la carte, and Vitalia is amenity-led with almost no services listed at all."}\n'
 ']},')
rep1(anchor, bracket, 'The Shape last item')

# ---------- 6. per-item source ids for the core chapters ----------
CORE_SRC = {
 'The Shape': [['agg_215','lopez'], ['agg_nostd','lopez'], ['agg_maint'],
               ['fivestar_phr','trilogy_phr','arrow_phr']],
 'The Six Functions': [['agg_maint'], ['agg_hk','justin_alc'], ['agg_din'],
                       ['agg_trans'], ['agg_well'], ['agg_le']],
 'Money': [['agg_fee'], ['agg_ef','witzgall'], ['research_noprice']],
 'The Tiers': [['gbb'], ['gbb_menu','wood','saxman'], ['call_capacity','kevin_ceiling']],
 'What Our Leaders Said': [['kevin_anchor'], ['kevin_delivery'], ['justin_alc','agg_hk'],
                           ['justin_4cond'], ['justin_flourish'], ['kevin_labor','call_capacity']],
 'What Not To Say': [['verify_cottage','cedarhurst'], ['radius'],
                     ['fabrications','verify_method'], ['call_rates','research_noprice']],
}
ch_start = h.index('var CH=[')
ch_end = h.index('\n];\n', ch_start) + 4
body = h[ch_start:ch_end]
chunks = re.split(r'(?=\{name:")', body)
out = [chunks[0]]
injected = 0
for ck in chunks[1:]:
    nm = re.match(r'\{name:"([^"]+)"', ck).group(1)
    must(nm in CORE_SRC, 'unexpected core chapter ' + nm)
    ids = CORE_SRC[nm]
    # item literals start at the beginning of a line with ' {n:"'
    parts = re.split(r'(?m)^(?= \{n:")', ck)
    items = parts[1:]
    must(len(items) == len(ids), '%s: %d items but %d source rows' % (nm, len(items), len(ids)))
    newitems = []
    for k, it in enumerate(items):
        tag = 's:[' + ','.join('"' + x + '"' for x in ids[k]) + '],'
        newitems.append(it.replace(' {n:"', ' {' + tag + 'n:"', 1))
        injected += 1
    out.append(parts[0] + ''.join(newitems))
newbody = ''.join(out)
h = h[:ch_start] + newbody + h[ch_end:]
print('source ids injected into %d core items' % injected)

# ---------- 7. data blocks before CH ----------
rep1('var CH=[', read('doss.js') + '\n' + read('src.js') + '\n' + read('opch.js') + '\nvar CH=[', 'CH open')

# ---------- 8. splice operator chapters in after the first two ----------
ch_end2 = h.index('\n];\n', h.index('var CH=[')) + 4
h = (h[:ch_end2] +
     '\n/* operator chapters sit between the market shape and the money, so the\n'
     '   portfolios are learned one at a time rather than in one boss answer */\n'
     'CH=CH.slice(0,2).concat(OPCH,CH.slice(2));\n' + h[ch_end2:])

# ---------- 9. bosses: one per chapter, keyed by name ----------
b0 = h.index('var BOSS=[')
b1 = h.index('\n];\n', b0) + 4
core_boss = read('coreboss.js')
h = h[:b0] + core_boss + '\nCH.forEach(function(c){ if(CORE_BOSS[c.name])c.boss=CORE_BOSS[c.name]; });\n' + h[b1:]

# ---------- 10. new UI functions ----------
rep1('/* ============ RENDER ============ */', read('ui_js.txt') + '/* ============ RENDER ============ */', 'render banner')

# ---------- 11. storage key + migration ----------
rep1('var KEY="cottage-drills-v2";', 'var KEY="cottage-drills-v3";', 'storage key')
rep1('try{var r=localStorage.getItem(KEY); if(r){S=Object.assign(S,JSON.parse(r)||{});}}catch(e){}',
 'try{var r=localStorage.getItem(KEY); if(r){S=Object.assign(S,JSON.parse(r)||{});}\n'
 '  else{ /* carry xp and badges over from the pre-dossier version; chapters renumbered */\n'
 '    var old=localStorage.getItem("cottage-drills-v2");\n'
 '    if(old){ var o=JSON.parse(old)||{};\n'
 '      S.xp=o.xp||0; S.best=o.best||0; S.right=o.right||0; S.wrong=o.wrong||0; S.badges=o.badges||{}; }\n'
 '  }}catch(e){}', 'state load')

# ---------- 12. render dispatch ----------
rep1('''function render(){
  rail(); hud();''', '''function render(){
  hud();
  if(MODE==="doss"){ return DIDX<0?renderDossList():renderDossOne(); }
  rail();''', 'render head')

# ---------- 13. rail: operator tag + operator bar ----------
rep1("""    b.innerHTML='<span class="dot"></span>'+c.name;""",
     """    b.innerHTML='<span class="dot"></span>'+c.name+(c.op?'<span class="optag">OP</span>':'');""",
     'chip inner')
rep1("""  document.getElementById("cFill").style.width=((S.i)/Q.length*100)+"%";
}""",
"""  document.getElementById("cFill").style.width=((S.i)/Q.length*100)+"%";
  opbar();
}

/* the strip that names the operator whose chapter you are in, with a way
   straight into its full dossier */
function opbar(){
  var el=document.getElementById("opbar"), c=CH[S.ch];
  if(!c.op){ el.className="opbar"; el.innerHTML=""; return; }
  var di=-1,i; for(i=0;i<DOSS.length;i++){ if(DOSS[i].n===c.op)di=i; }
  var o=di>=0?DOSS[di]:null;
  el.className="opbar on";
  el.innerHTML='<span class="onm">'+c.op+'</span>'+
    (o?'<span class="ometa">'+o.ns+' communities &middot; '+o.units+' villas</span>':'')+
    (o?'<span class="ogo"><button class="minibtn" type="button" id="opgo">Open the full dossier</button></span>':'');
  var g=document.getElementById("opgo");
  if(g)g.addEventListener("click",function(){ SFX.tick(); DIDX=di; setMode("doss"); });
}""", 'rail tail')

# ---------- 14. learn card: source panel ----------
rep1("""    '<div class="say"><div class="lab">Say it like this</div><p>'+d.say+'</p></div>'+
    '<div class="actions"><button class="btn" type="button" id="got">Got it</button></div></div>';""",
"""    '<div class="say"><div class="lab">Say it like this</div><p>'+d.say+'</p></div>'+
    srcHTML(d.s)+
    '<div class="actions"><button class="btn" type="button" id="got">Got it</button></div></div>';""",
 'learn card')

# ---------- 15. quiz reveal: source panel ----------
rep1("""        '<div class="say"><div class="lab">Say it like this</div><p>'+d.say+'</p></div>'+
        '<div class="actions"><button class="btn" type="button" id="nx">Next</button></div>';""",
"""        '<div class="say"><div class="lab">Say it like this</div><p>'+d.say+'</p></div>'+
        srcHTML(d.s)+
        '<div class="actions"><button class="btn" type="button" id="nx">Next</button></div>';""",
 'quiz reveal')

# ---------- 16. boss round: per-chapter, with sources ----------
r0 = h.index('function renderBoss(step){')
r1 = h.index('function finishChapter()')
h = h[:r0] + read('boss_render.js') + h[r1:]

# ---------- 17. controls ----------
rep1("""document.getElementById("reset").addEventListener("click",function(){
  S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0};
  save(); Q=queueFor(0); render();
});""",
"""document.getElementById("reset").addEventListener("click",function(){
  S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0};
  save(); Q=queueFor(0); MODE="drill"; DIDX=-1; setMode("drill");
});
document.getElementById("mode").addEventListener("click",function(){
  SFX.tick(); setMode(MODE==="doss"?"drill":"doss");
});""", 'reset control')

# ---------- 18. footer line ----------
rep1('Every figure comes from the benchmark workbook. Learn cards teach it, drill cards prove it, boss rounds are what an owner will actually ask.',
     'Every figure comes from the benchmark workbook, and every card shows its source. Learn cards teach it, drill cards prove it, boss rounds are what an owner will actually ask. Where no public page was captured, the panel says so instead of guessing a link.',
     'footer')

io.open(P, 'w', encoding='utf-8').write(h)
print('drills.html: %d -> %d bytes' % (orig_len, len(h)))
