/* Griz HQ scoreboard — cache-authoritative renderer.
   The browser intentionally does not call ESPN. GitHub Actions generates
   scoreboard/scoreboard-data.json and this file renders that cache only. */
(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;
  if(!C)return;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,'');
  const same=(a,b)=>{
    const x=norm(a),y=norm(b);
    return !!x&&!!y&&(x===y||x.startsWith(y)||y.startsWith(x));
  };
  const teamName=t=>t?.name||t?.short||'Team';
  const teams=e=>Array.isArray(e?.teams)?e.teams:[];
  const logo=t=>t?.logo||(t?.id?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(t.id)}.png`:'');
  const status=e=>{
    const s=e?.status||{};
    if(s.completed||s.state==='post'||s.name==='STATUS_FINAL')return 'FINAL';
    if(s.state==='in'||s.name==='STATUS_IN_PROGRESS')return s.shortDetail||'LIVE';
    return s.shortDetail||s.detail||'SCHEDULED';
  };
  const fmt=s=>new Date(String(s).slice(0,10)+'T12:00:00Z')
    .toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  const card=e=>{
    const ts=teams(e);
    const a=ts.find(t=>t.homeAway==='away')||ts[0];
    const h=ts.find(t=>t.homeAway==='home')||ts[1];
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${logo(t)?`<img src="${esc(logo(t))}" alt="" loading="lazy">`:''}<span>${esc(teamName(t))}</span></span><strong>${esc(t?.score??'—')}</strong></div>`;
    return `<a class="ghq-score-card" href="https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(e.id||'')}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(fmt(e.date))}</span><b>ESPN</b></div>${row(a)}${row(h)}<div class="ghq-score-status">${esc(status(e))}</div></a>`;
  };
  const empty=(rank,nm,bye)=>`<div class="ghq-score-card ghq-score-empty"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(nm)}</span></div><div class="ghq-score-status">${bye?'BYE — NO GAME THIS WEEK':'NO MATCHUP FOUND IN VERIFIED CACHE'}</div></div>`;
  const weekIndex=()=>{
    const now=new Date().toISOString().slice(0,10);
    const active=C.weeks.findIndex(w=>now>=w[0]&&now<=w[1]);
    if(active>=0)return active;
    const upcoming=C.weeks.findIndex(w=>w[0]>now);
    return upcoming>=0?upcoming:C.weeks.length-1;
  };
  async function loadCache(){
    const r=await fetch('scoreboard/scoreboard-data.json?cache='+Date.now(),{cache:'no-store'});
    if(!r.ok)throw Error('scoreboard cache HTTP '+r.status);
    const d=await r.json();
    if(!Array.isArray(d.weeks)||!Array.isArray(d.rankings))throw Error('invalid scoreboard cache');
    return d;
  }
  async function render(){
    const weekEl=$('fcs-week-filter'),top=$('fcs-top20'),big=$('bigsky-score-games'),st=$('fcs-status');
    if(!weekEl||!top||!big)return;
    if(!weekEl.dataset.ready){
      C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});
      weekEl.dataset.ready='1';
    }
    if(!weekEl.dataset.userChanged)weekEl.value=String(weekIndex());
    const index=Number(weekEl.value)||0;
    const w=C.weeks[index];
    top.innerHTML='<div class="ghq-score-empty">Loading verified scoreboard cache…</div>';
    big.innerHTML='';
    if(st)st.textContent='Loading verified scoreboard cache…';
    try{
      const d=await loadCache();
      const cached=d.weeks.find(x=>Number(x.index)===index)||d.weeks[index];
      if(!cached)throw Error('week '+index+' missing from cache');
      const rankings=d.rankings.slice(0,25);
      const games=Array.isArray(cached.fcsTop25Games)?cached.fcsTop25Games:[];
      const byes=new Set((cached.fcsTop25Byes||[]).map(r=>norm(r.team||r.name)));
      const rankedCards=rankings.map((r,i)=>{
        const nm=r.team||r.name||'';
        const e=games.find(g=>teams(g).some(t=>same(nm,teamName(t))));
        return e?card(e):empty(r.rank||i+1,nm,byes.has(norm(nm)));
      });
      top.innerHTML=rankedCards.join('');
      const bs=Array.isArray(cached.bigSkyGames)?cached.bigSkyGames:[];
      big.innerHTML=bs.length?bs.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(card).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
      if(st)st.textContent=`Loaded verified cache • ${games.length} ranked games • ${bs.length} Big Sky games • ${cached.label||w[2]}`;
    }catch(err){
      top.innerHTML='<div class="ghq-score-empty"><b>SCOREBOARD CACHE UNAVAILABLE</b><span>The verified scoreboard file could not be loaded.</span></div>';
      big.innerHTML='<div class="ghq-score-empty">SCOREBOARD CACHE UNAVAILABLE</div>';
      if(st)st.textContent='Verified scoreboard cache unavailable';
      console.error('Griz scoreboard',err);
    }
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');
  if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();