/* Griz HQ scoreboard — cache-first renderer. */
(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;
  if(!C)return;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,'');
  const comp=ev=>ev?.competitions?.[0];
  const teams=ev=>ev?.teams||comp(ev)?.competitors||[];
  const teamName=t=>t?.name||t?.team?.displayName||t?.team?.shortDisplayName||t?.team?.name||'Team';
  const teamId=t=>String(t?.id||t?.team?.id||'');
  const teamLogo=t=>t?.logo||t?.team?.logo||(teamId(t)?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(teamId(t))}.png`:'');
  const eventStatus=ev=>{const s=ev?.status||comp(ev)?.status?.type||{};if(s.completed)return 'FINAL';if(s.state==='in'||s.name==='STATUS_IN_PROGRESS')return s.shortDetail||'LIVE';return s.shortDetail||s.detail||'SCHEDULED';};
  const dateLabel=s=>{if(!s)return '';const d=new Date(String(s).slice(0,10)+'T12:00:00Z');return Number.isNaN(d.getTime())?'':d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});};
  const rankingAliases={
    'montanastate':['montanast','montanastate','montanastateuniversity'],
    'portlandstate':['portlandst','portlandstate'],
    'northernarizona':['northernarizona','nau'],
    'ucdavis':['ucdavis','ucdavisaggies'],
    'stephenfaustin':['stephenfaustin','sfasu','stephenfaustinstate'],
    'austinpeay':['austinpeay'],
    'southdakotastate':['southdakotastate','sdsu'],
    'southdakota':['southdakota','usd'],
    'northdakota':['northdakota','und'],
    'northdakotastate':['northdakotastate','ndsu'],
    'ucf':['ucf','centralflorida']
  };
  const aliasSet=key=>new Set([key,...(rankingAliases[key]||[])]);
  function findRankingIndex(candidate,rankings){
    const n=norm(candidate);if(!n)return -1;
    const hits=[];
    rankings.forEach((r,i)=>{const key=norm(r.team||r.name);for(const a of aliasSet(key)){if(n===a||n.startsWith(a)){hits.push({i,len:a.length});break;}}});
    hits.sort((a,b)=>b.len-a.len);return hits.length?hits[0].i:-1;
  }
  function card(ev){
    const ts=teams(ev),a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1];
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${teamLogo(t)?`<img src="${esc(teamLogo(t))}" alt="" loading="lazy">`:''}<span>${esc(teamName(t))}</span></span><strong>${esc(t?.score??'—')}</strong></div>`;
    const id=ev?.id?`https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(ev.id)}`:'#';
    return `<a class="ghq-score-card" href="${id}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(dateLabel(ev.date))}</span><b>ESPN</b></div>${row(a)}${row(h)}<div class="ghq-score-status">${esc(eventStatus(ev))}</div></a>`;
  }
  function empty(rank,nm){return `<div class="ghq-score-card ghq-score-empty"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(nm)}</span></div><div class="ghq-score-status">NO MATCHUP FOUND IN ESPN FEED</div></div>`;}
  function weekIndex(){const now=new Date().toISOString().slice(0,10);const active=C.weeks.findIndex(w=>now>=w[0]&&now<=w[1]);if(active>=0)return active;const upcoming=C.weeks.findIndex(w=>w[0]>now);return upcoming>=0?upcoming:C.weeks.length-1;}
  async function loadCache(){const r=await fetch('scoreboard/scoreboard-data.json?cache='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('scoreboard cache '+r.status);return r.json();}
  async function render(){
    const weekEl=$('fcs-week-filter'),top=$('fcs-top20'),big=$('bigsky-score-games'),st=$('fcs-status');if(!weekEl||!top||!big)return;
    if(!weekEl.dataset.ready){C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});weekEl.dataset.ready='1';}
    if(!weekEl.dataset.userChanged)weekEl.value=String(weekIndex());
    const wi=Number(weekEl.value)||0,w=C.weeks[wi];top.innerHTML='<div class="ghq-score-empty">Loading verified scoreboard cache…</div>';big.innerHTML='';if(st)st.textContent='Loading scores…';
    try{
      const cache=await loadCache();const row=(cache.weeks||[]).find(x=>Number(x.index)===wi)||cache.weeks?.[wi];
      if(!row)throw Error('No cached week '+wi);
      const rankings=(cache.rankings||[]).slice(0,25);const events=row.fcsEvents||row.fcsTop25Games||[];const bs=row.bigSkyEvents||row.bigSkyGames||[];
      top.innerHTML=rankings.map((r,i)=>{const idx=events.findIndex(e=>teams(e).some(t=>findRankingIndex(teamName(t),rankings)===i));return idx>=0?card(events[idx]):empty(r.rank||i+1,r.team||r.name||'');}).join('');
      big.innerHTML=bs.length?bs.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(card).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
      if(st)st.textContent=`Loaded ${events.length} verified FCS events • ${bs.length} Big Sky events • ${w[2]}`;
    }catch(err){top.innerHTML='<div class="ghq-score-empty"><b>SCHEDULE DATA UNAVAILABLE</b><span>Verified scoreboard cache could not be loaded.</span></div>';big.innerHTML='<div class="ghq-score-empty">SCHEDULE DATA UNAVAILABLE</div>';if(st)st.textContent='Schedule data unavailable';console.error('Griz scoreboard',err);}
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();
