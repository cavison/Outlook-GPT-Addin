function renderBoss(step){
  var c=CH[step.ci], d=c.boss;
  if(!d){ return finishChapter(); }
  stage.innerHTML='<div class="card"><span class="kind k-boss">Boss round — '+
    (c.op?'you are in the room about '+c.op:'an owner asks')+'</span>'+
    '<h2 class="q">“'+d.q+'”</h2>'+
    '<p class="ctx" style="margin-top:10px">Say your answer out loud, then reveal. No peeking — the whole point is producing it.</p>'+
    '<div class="actions"><button class="btn" type="button" id="rev">I answered it — reveal</button></div></div>';
  document.getElementById("rev").addEventListener("click",function(){
    SFX.tick();
    stage.innerHTML='<div class="card"><span class="kind k-boss">Boss round</span>'+
      '<h2 class="q">“'+d.q+'”</h2>'+
      '<div class="res"><div class="say"><div class="lab">A strong answer</div><p>'+d.say+'</p></div>'+
      '<p class="why" style="margin-top:12px"><strong>Evidence:</strong> '+d.ev+'</p>'+
      srcHTML(d.s,"Every claim in that answer — click to check it")+
      '<div class="actions"><button class="btn" type="button" id="y">I had that — +60</button>'+
      '<button class="btn ghost" type="button" id="n">Not yet — +15</button></div></div></div>';
    document.getElementById("y").addEventListener("click",function(){ SFX.right(3); award(60); finishChapter(); });
    document.getElementById("n").addEventListener("click",function(){ SFX.tick(); award(15); finishChapter(); });
  });
}
