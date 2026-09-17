/* Griz HQ scoreboard — cache-first renderer. */
(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;
  if(!C)return;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,'');
  const id=c=>String(c?.id||c?.team?.id||'');
  const name=c=>c?.name||c?.short||c?.team?.displayName||c?.team?.shortDisplayName||c?.displayName||c?.team?.name||'Team';
  const logo=c=>c?.logo||c?.team?.logo||(id(c)?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id(c))}.png`:'');
  const teams=ev=>ev?.teams||ev?.competitions?.[0]?.competitors||[];
  const status=ev=>{
    const s=ev?.status||ev?.competitions?.[0]?.status?.type||{};
    if(s.completed)return 'FINAL';
    if(s.state==='in'||s.name==='STATUS_IN_PROGRESS')return s.shortDetail||'LIVE';
    return s.shortDetail||s.detail||'SCHEDULED';
  };
  const fmt=s=>{const d=new Date(String(s).slice(0,10)+'T12:00:00Z');return Number.isNaN(d.getTime())?'':d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});};
  const weekIndex=()=>{
    const now=new Date().toISOString().slice(0,10);
    const active=C.weeks.findIndex(w=>now>=w[0]&&now<=w[1]);
    if(active>=0)return active;
    const upcoming=C.weeks.findIndex(w=>w[0]>now);
    return upcoming>=0?upcoming:C.weeks.length-1;
  };
  function card(ev){
    const ts=teams(ev),a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1];
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${logo(t)?`<img src="${esc(logo(t))}" alt="" loading="lazy">`:''}<span>${esc(name(t))}</span></span><strong>${esc(t?.score??'—')}</strong></div>`;
    return `<a class="ghq-score-card" href="https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(ev.id||'')}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(fmt(ev.date))}</span><b>ESPN</b></div>${row(a)}${row(h)}<div class="ghq-score-status">${esc(status(ev))}</div></a>`;
  }
  function empty(rank,nm){return `<div class="ghq-score-card ghq-score-empty"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(nm)}</span></div><div class="ghq-score-status">NO MATCHUP FOUND IN VERIFIED CACHE</div></div>`;}
  async function loadCache(){
    const r=await fetch('scoreboard/scoreboard-data.json?cache='+Date.now(),{cache:'no-store'});
    if(!r.ok)throw Error('scoreboard cache '+r.status);
    return r.json();
  }
  async function render(){
    const weekEl=$('fcs-week-filter'),top=$('fcs-top20'),big=$('bigsky-score-games'),st=$('fcs-status');
    if(!weekEl||!top||!big)return;
    if(!weekEl.dataset.ready){C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});weekEl.dataset.ready='1';}
    if(!weekEl.dataset.userChanged)weekEl.value=String(weekIndex());
    const idx=Number(weekEl.value)||0,w=C.weeks[idx];
    top.innerHTML='<div class="ghq-score-empty">Loading verified scoreboard cache…</div>';big.innerHTML='';if(st)st.textContent='Loading verified scores…';
    try{
      const data=await loadCache();
      const cached=data.weeks?.find(x=>Number(x.index)===idx)||data.weeks?.[idx];
      if(!cached)throw Error('No cache entry for week '+idx);
      const rankings=(data.rankings||[]).slice(0,25);
      const games=cached.fcsTop25Games||[];
      const byes=new Map((cached.fcsTop25Byes||[]).map(x=>[norm(x.team),x]));
      const played=new Set(games.flatMap(e=>teams(e).map(name).map(norm)));
      top.innerHTML=rankings.map((r,i)=>{
        const key=norm(r.team);
        const ev=games.find(e=>teams(e).some(t=>norm(name(t))===key||norm(name(t)).startsWith(key)||key.startsWith(norm(name(t)))));
        return ev?card(ev):empty(r.rank||i+1,r.team);
      }).join('');
      const bs=cached.bigSkyGames||[];
      big.innerHTML=bs.length?bs.sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(card).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
      if(st)st.textContent=`Loaded ${games.length} ranked FCS games + ${bs.length} Big Sky games from verified cache • ${w[2]}`;
    }catch(err){
      top.innerHTML='<div class="ghq-score-empty"><b>SCOREBOARD CACHE UNAVAILABLE</b><span>Run the GitHub scoreboard refresh and try again.</span></div>';
      big.innerHTML='<div class="ghq-score-empty">SCOREBOARD CACHE UNAVAILABLE</div>';
      if(st)st.textContent='Verified scoreboard cache unavailable';
      console.error('Griz scoreboard',err);
    }
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();
