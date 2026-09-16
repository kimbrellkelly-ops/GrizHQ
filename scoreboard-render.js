(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;if(!C)return;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const aliases={
    southdakotastate:['southdakotastate','southdakotastatejackrabbits','sdstate','sdst'],
    southdakota:['southdakota','southdakotacoyotes'], montanastate:['montanastate','montanastatebobcats'],
    montana:['montana','montanagrizzlies'], idahostate:['idahostate','idahostatebengals'], idaho:['idaho','idahovandals'],
    youngstownstate:['youngstownstate','youngstownst'], stephenfaustin:['stephenfaustin','sfa'], williammary:['williammary','williamandmary'],
    southernillinois:['southernillinois','southernillinoissalukis'], westflorida:['westflorida','westfloridaargos'],
    northernarizona:['northernarizona','northernarizonalumberjacks'], northerncolorado:['northerncolorado','northerncoloradobears'],
    easternwashington:['easternwashington','easternwashingtoneagles'], portlandstate:['portlandstate','portlandstatevikings'],
    weberstate:['weberstate','weberstatewildcats'], southernutah:['southernutah','southernutahthunderbirds'],
    utahtech:['utahtech','utahtechtrailblazers'], calpoly:['calpoly','calpolymustangs'], ucdavis:['ucdavis','ucdavisaggies']
  };
  function same(a,b){const x=norm(a),y=norm(b);if(x===y)return true;for(const [k,v] of Object.entries(aliases)){if((x===k||v.includes(x))&&(y===k||v.includes(y)))return true;}return false;}
  function tname(t){return t?.name||t?.short||t?.abbreviation||'Team';}
  function logo(t){return t?.logo||'';}
  function status(e){const s=e?.status||{};if(s.completed)return 'FINAL';if(s.state==='in'||s.state==='halftime'||s.state==='endperiod')return s.shortDetail||'LIVE';return s.shortDetail||s.detail||'SCHEDULED';}
  function dateText(s){const d=new Date(s);return Number.isNaN(d.getTime())?'':d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});}
  function currentWeek(){const now=new Date();let i=C.weeks.findIndex(w=>now>=new Date(w[0]+'T00:00:00')&&now<=new Date(w[1]+'T23:59:59'));if(i>=0)return i;const future=C.weeks.findIndex(w=>new Date(w[0]+'T00:00:00')>now);return future>=0?future:C.weeks.length-1;}
  function teamRank(n,rs){const r=rs.find(x=>same(x.team,n));return r?`#${r.rank}`:'';}
  function eventFor(r,events){return events.find(e=>(e.teams||[]).some(t=>same(clean(r.team),tname(t))));}
  function card(e,rs){
    const ts=e.teams||[],a=ts.find(t=>t.homeAway==='away')||ts[0]||{},h=ts.find(t=>t.homeAway==='home')||ts[1]||{};
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-name">${logo(t)?`<img class="ghq-score-logo" src="${esc(logo(t))}" alt="" loading="lazy">`:''}<span>${teamRank(tname(t),rs)?`<span class="ghq-score-rank">${esc(teamRank(tname(t),rs))}</span>`:''}${esc(tname(t))}</span></span><strong class="ghq-score-number">${esc(t.score??'—')}</strong></div>`;
    const href=e.id?`https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(e.id)}`:'#';
    return `<a class="ghq-fcs-card ghq-score-card" href="${href}" target="_blank" rel="noopener"><div class="ghq-score-head"><span>${esc(dateText(e.date))}</span><b>${esc((e.broadcasts||[])[0]||'ESPN')}</b></div>${row(a)}${row(h)}<div class="ghq-score-foot"><span class="ghq-score-status">${esc(status(e))}</span><span>${esc(e.venue||'')}</span></div></a>`;
  }
  function unavailable(r){return `<div class="ghq-fcs-card ghq-score-unavailable"><strong>SCHEDULE DATA UNAVAILABLE</strong><span>#${esc(r.rank)} ${esc(clean(r.team))}</span></div>`;}
  function topStripCard(e,rs){return card(e,rs).replace('ghq-fcs-card','v2-score-card ghq-fcs-card');}
  async function loadCache(){const r=await fetch(`scoreboard/scoreboard-data.json?ts=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw Error(`scoreboard cache ${r.status}`);return r.json();}
  async function render(){
    const weekEl=document.getElementById('fcs-week-filter'),top=document.getElementById('fcs-top20'),big=document.getElementById('bigsky-score-games'),strip=document.getElementById('score-games'),group=document.getElementById('score-group-select'),weekStrip=document.getElementById('score-week-select'),refresh=document.getElementById('fcs-refresh'),st=document.getElementById('fcs-status');
    if(!top&&!strip)return;
    if(weekEl&&!weekEl.dataset.ghqReady){C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o)});weekEl.value=String(currentWeek());weekEl.dataset.ghqReady='1';weekEl.addEventListener('change',render);}
    if(weekStrip&&!weekStrip.dataset.ghqReady){weekStrip.replaceChildren(...C.weeks.map((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`Week ${i}`;return o;}));weekStrip.value=String(currentWeek());weekStrip.dataset.ghqReady='1';}
    const i=Number(weekEl?.value??weekStrip?.value??currentWeek()),w=C.weeks[i]||C.weeks[currentWeek()];
    try{
      const data=await loadCache(),wd=(data.weeks||[]).find(x=>x.index===i);if(!wd)throw Error('selected week is not cached yet');
      const rs=(data.rankings||[]).slice(0,25),f=wd.fcsEvents||[],b=wd.bigSkyEvents||[];
      if(top)top.innerHTML=rs.map(r=>{const e=eventFor(r,f);return e?card(e,rs):unavailable(r)}).join('');
      if(big)big.innerHTML=b.length?b.map(e=>`<div class="fcs-game bigsky-row">${card(e,rs)}</div>`).join(''):'<div class="ghq-score-unavailable">NO BIG SKY GAMES THIS WEEK</div>';
      if(strip){const g=(group?.value||'fcs')==='bigsky'?b:f.filter(e=>e.teams?.some(t=>rs.some(r=>same(r.team,tname(t)))));strip.replaceChildren(...g.map(e=>{const d=document.createElement('div');d.innerHTML=topStripCard(e,rs);return d.firstElementChild;}));strip.scrollLeft=0;}
      if(st)st.textContent=`Verified ESPN cache • ${wd.fcsEventCount} FCS events • ${wd.bigSkyEventCount} Big Sky games • ${w[2]}`;
      const rd=document.getElementById('fcs-rankings-date');if(rd&&data.rankingsDate)rd.textContent=`Stats Perform • ${data.rankingsDate}`;
    }catch(e){
      console.error('Griz HQ scoreboard',e);if(top)top.innerHTML=`<div class="ghq-score-unavailable"><strong>SCOREBOARD DATA UNAVAILABLE</strong><span>${esc(e.message||'Verified cache unavailable')}</span></div>`;if(big)big.innerHTML='<div class="ghq-score-unavailable"><strong>SCOREBOARD DATA UNAVAILABLE</strong><span>Wait for the scoreboard refresh to complete.</span></div>';if(strip)strip.innerHTML='<div class="v2-score-card v2-score-empty"><strong>Scores unavailable</strong><small>Verified scoreboard cache is unavailable.</small></div>';if(st)st.textContent='Scoreboard cache unavailable';
    }
  }
  const g=document.getElementById('score-group-select'),w=document.getElementById('score-week-select'),r=document.getElementById('fcs-refresh');
  g?.addEventListener('change',render);w?.addEventListener('change',render);r?.addEventListener('click',render);
  window.GrizScoreboard={render};window.renderFCSScoreboard=render;
  render();setInterval(render,60000);
})();
