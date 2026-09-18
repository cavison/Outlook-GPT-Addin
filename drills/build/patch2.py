# -*- coding: utf-8 -*-
"""Second pass: rescale the rank ladder to the larger content set, add an
operator badge per portfolio cleared, and reward actually opening a source."""
import io, os, sys
SP = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(SP, 'art', 'drills.html')
h = io.open(P, encoding='utf-8').read()

def rep1(old, new, label):
    global h
    if h.count(old) != 1:
        print('FAIL', label, h.count(old)); sys.exit(1)
    h = h.replace(old, new)

# --- ranks: 10 levels across the ~6,500 XP the full run now yields ---
rep1('''var RANKS=[
 {xp:0,n:"Skimming"},{xp:120,n:"Getting the Shape"},{xp:300,n:"Knows the Core"},
 {xp:540,n:"Briefing Ready"},{xp:820,n:"Owner Ready"},{xp:1150,n:"Owns the Room"},{xp:1550,n:"Wrote the Playbook"}
];''',
'''var RANKS=[
 {xp:0,n:"Skimming"},{xp:250,n:"Getting the Shape"},{xp:700,n:"Knows the Core"},
 {xp:1300,n:"Knows the Operators"},{xp:2000,n:"Briefing Ready"},{xp:2800,n:"Owner Ready"},
 {xp:3600,n:"Speaks Operator"},{xp:4500,n:"Owns the Room"},{xp:5400,n:"Cold on Every Portfolio"},
 {xp:6200,n:"Wrote the Playbook"}
];''', 'ranks')

# --- a badge for each operator portfolio cleared ---
rep1('''  var first=!S.done["ch"+S.ch];
  if(first){ S.done["ch"+S.ch]=1; save(); SFX.chapter(); confetti();
    var all=CH.every(function(c,i){return S.done["ch"+i];});
    if(all)badge("allch","🏆","Every chapter cleared","You have been through the whole brief. Run the weak ones again.");
  }''',
'''  var first=!S.done["ch"+S.ch];
  if(first){ S.done["ch"+S.ch]=1; save(); SFX.chapter(); confetti();
    var c=CH[S.ch];
    if(c.op)badge("op-"+S.ch,"🏛️",c.op+" briefed","You can hold that conversation now. Their whole portfolio, not one site.");
    var ops=CH.filter(function(x){return x.op;});
    var allops=ops.every(function(x){return S.done["ch"+CH.indexOf(x)];});
    if(allops)badge("allops","🗺️","Every operator learned","Eight portfolios, fifty communities. You know who does what.");
    var all=CH.every(function(x,i){return S.done["ch"+i];});
    if(all)badge("allch","🏆","Every chapter cleared","You have been through the whole brief. Run the weak ones again.");
  }''', 'chapter done badges')

# --- reward opening a source, because that is the habit worth building ---
rep1('''document.addEventListener("click",function once(){ ac(); document.removeEventListener("click",once); },{once:true});''',
'''/* opening a source is the habit worth rewarding, so it scores */
document.addEventListener("click",function(e){
  var a=e.target&&e.target.closest?e.target.closest(".srclinks a"):null;
  if(!a)return;
  S.checked=(S.checked||0)+1; save();
  award(15); SFX.learn();
  if(S.checked===1)badge("recpt1","🔎","Checked a source","That link is the difference between briefing an owner and reading them a deck.");
  if(S.checked===5)badge("recpt5","📎","Five receipts pulled","You are now harder to argue with than the research is.");
});
document.addEventListener("click",function once(){ ac(); document.removeEventListener("click",once); },{once:true});''',
 'source click reward')

# --- keep the new counter in the state shape and the reset ---
h = h.replace('var S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0};',
              'var S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0,checked:0};')
h = h.replace('  S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0};',
              '  S={xp:0,streak:0,best:0,ch:0,i:0,done:{},badges:{},right:0,wrong:0,checked:0};')

# --- show the source count on the chapter-done scoreboard ---
rep1("""    '<div><b>'+S.right+'</b><span>drills right</span></div></div>'+""",
     """    '<div><b>'+S.right+'</b><span>drills right</span></div>'+
    '<div><b>'+(S.checked||0)+'</b><span>sources opened</span></div></div>'+""",
 'scorerow')

io.open(P, 'w', encoding='utf-8').write(h)
print('patch2 applied, %d bytes' % len(h))
