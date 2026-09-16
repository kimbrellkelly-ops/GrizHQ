/* Griz HQ — scoreboard renderer. Data is refreshed server-side by GitHub Actions. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=s=>String(s||'').toLowerCase().replace(/\s*\([^)]*\)\s*$/,'').replace(/[^a-z0-9]/g,'');
  const same=(a,b)=>{const x=norm(a),y=norm(b);return !!x&&!!y&&(x===y||x.includes(y)||y.includes(x));};
  const fmt=d=>{const x=new Date(d);return Number.isNaN(x.getTime())?'':x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});};
  const state=e=>e?.status?.completed?'FINAL':e?.status?.state==='in'?'LIVE':(e?.status?.detail||'SCHEDULED');
  const teamRow=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${t.logo?`<img src="${esc(t.logo)}" alt="" loading="lazy">`:''}<span>${esc(t.name)}</span></span><strong>${esc(t.score??'—')}</strong></div>`;
  function eventCard(e,rank){
    const ts=e.teams||[],away=ts.find(t=>t.homeAway==='away')||ts[0],home=ts.find(t=>t.homeAway==='home')||ts[1];
    if(!away||!home)return '';
    return `<a class="ghq-score-card" href="https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(e.id)}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(fmt(e.date))}</span><b>${rank?`#${esc(rank)} `:''}${esc(state(e))}</b></div>${teamRow(away)}${teamRow(home)}<div class="ghq-score-status">${esc(e.venue||'ESPN')}</div></a>`;
  }
  function byeCard(rank,name){return `<div class="ghq-score-card ghq-score-bye"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(name)}</span></div><div class="ghq-score-status">BYE / NO GAME THIS WEEK</div></div>`;}
  function findGame(events,name){return events.find(e=>(e.teams||[]).some(t=>same(name,t.name)||same(name,t.shortName)||same(name,t.abbreviation)));}
  function chooseWeek(weeks){
    const now=new Date().toISOString().slice(0,10);
    let i=weeks.findIndex(w=>now>=w.start&&now<=w.end);
    if(i>=0)return i;
    i=weeks.findIndex(w=>now<w.start);
    return i>=0?i:weeks.length-1;
  }
  async function render(){
    const weekEl=$('fcs-week-filter'),top=$('fcs-top20'),big=$('bigsky-score-games'),st=$('fcs-status');
    if(!weekEl||!top||!big)return;
    try{
      const r=await fetch('scoreboard/scoreboard-data.json?v='+Date.now(),{cache:'no-store'});
      if(!r.ok)throw Error('Scoreboard cache '+r.status);
      const data=await r.json(),weeks=data.weeks||[],rankings=(data.rankings||[]).slice(0,25);
      if(!weeks.length)throw Error('No scoreboard weeks');
      if(!weekEl.dataset.ready){weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w.label;weekEl.appendChild(o);});weekEl.dataset.ready='1';}
      if(!weekEl.dataset.userChanged)weekEl.value=String(chooseWeek(weeks));
      const w=weeks[Number(weekEl.value)||0],events=w.events||[];
      top.classList.add('ghq-score-grid');
      big.classList.add('ghq-score-grid','ghq-score-bigsky');
      top.innerHTML=rankings.map(r=>eventCard(findGame(events,r.team),r.rank)||byeCard(r.rank,r.team)).join('');
      const bigIds=new Set(['149','147','302','2464','304','3101','310','253','2459','20','244','275','311','2448']);
      const bs=events.filter(e=>(e.teams||[]).some(t=>bigIds.has(String(t.id))));
      big.innerHTML=bs.length?bs.map(e=>eventCard(e)).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
      if(st)st.textContent=`ESPN data • ${w.label} • Updated ${new Date(data.generatedAt).toLocaleString('en-US')}`;
    }catch(err){
      top.innerHTML='<div class="ghq-score-empty"><b>SCOREBOARD DATA UNAVAILABLE</b><span>Waiting for the verified ESPN scoreboard cache.</span></div>';
      big.innerHTML='<div class="ghq-score-empty">SCOREBOARD DATA UNAVAILABLE</div>';
      if(st)st.textContent='Scoreboard data unavailable';
      console.error('Griz scoreboard',err);
    }
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');
  if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();
