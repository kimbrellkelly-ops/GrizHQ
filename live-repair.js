(function(){
  'use strict';
  function text(el, value){ if(el && value != null) el.textContent=String(value); }
  function esc(v){ return String(v ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
  function installScroll(){
    const box=document.getElementById('score-games');
    const prev=document.querySelector('.v2-score-prev');
    const next=document.querySelector('.v2-score-next');
    if(!box || box.dataset.repairScroll==='1') return;
    box.dataset.repairScroll='1';
    box.style.overflowX='auto'; box.style.display='flex'; box.style.scrollBehavior='smooth'; box.style.gap='12px';
    if(prev) prev.addEventListener('click',()=>box.scrollBy({left:-Math.max(260,box.clientWidth*.8),behavior:'smooth'}));
    if(next) next.addEventListener('click',()=>box.scrollBy({left:Math.max(260,box.clientWidth*.8),behavior:'smooth'}));
  }
  function renderNext(d){
    const g=d && d.next_game; if(!g) return;
    const opp=String(g.opponent||'Opponent'), date=String(g.date||''), time=String(g.time||''), venue=String(g.venue||'');
    document.querySelectorAll('.ghq-nu-hero h1 span').forEach(e=>text(e,opp.toUpperCase()));
    document.querySelectorAll('.ghq-nu-team.is-opponent h2').forEach(e=>text(e,opp.toUpperCase()));
    document.querySelectorAll('.ghq-nu-game-pill b').forEach(e=>text(e,date.toUpperCase()));
    document.querySelectorAll('.ghq-nu-game-pill span').forEach(e=>text(e,time));
    document.querySelectorAll('.ghq-nu-game-pill small').forEach(e=>text(e,venue));
    document.querySelectorAll('.v2-home-next-match').forEach(e=>{e.innerHTML='<div><strong>GRIZ</strong><small>MONTANA<br>'+esc(d.team?.record||'—')+'</small></div><div><b>'+esc(date)+'<br>'+esc(time)+'</b><small>'+esc(g.tv||g.network||'TBA')+'</small></div><div><strong>'+esc(opp.slice(0,3).toUpperCase())+'</strong><small>'+esc(opp)+'<br>UPCOMING</small></div>';});
    document.querySelectorAll('.v2-home-next p').forEach(e=>text(e,venue));
    document.querySelectorAll('.v2-snapshot-grid > div:first-child b').forEach(e=>text(e,d.team?.record||'—'));
    document.querySelectorAll('.v2-snapshot-grid > div:nth-child(3) b').forEach(e=>text(e,d.team?.conference_record||'—'));
  }
  function boot(){installScroll();fetch('data.json?repair='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{renderNext(d);}).catch(()=>{});}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
