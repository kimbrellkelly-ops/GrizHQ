/* Griz HQ scoreboard — independent renderer. */
(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;
  if(!C)return;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,'');
  const same=(a,b)=>{const x=norm(a),y=norm(b);return !!x&&!!y&&(x===y||x.includes(y)||y.includes(x));};
  const name=c=>c?.team?.displayName||c?.team?.shortDisplayName||c?.team?.name||c?.displayName||c?.name||'Team';
  const id=c=>String(c?.team?.id||c?.id||'');
  const logo=c=>c?.team?.logo||c?.logo||(id(c)?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id(c))}.png`:'');
  const comp=ev=>ev?.competitions?.[0];
  const teams=ev=>comp(ev)?.competitors||[];
  const status=ev=>{const s=comp(ev)?.status?.type||{};if(s.completed)return 'FINAL';if(s.state==='in'||s.name==='STATUS_IN_PROGRESS')return s.shortDetail||'LIVE';return s.shortDetail||s.detail||'SCHEDULED';};
  const fmt=s=>new Date(String(s).slice(0,10)+'T12:00:00Z').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  const weekIndex=()=>{const now=new Date().toISOString().slice(0,10);const i=C.weeks.findIndex(w=>now>=w[0]&&now<=w[1]);return i<0?Math.max(0,C.weeks.length-1):i;};
  async function fetchWeek(w){
    const out=[],seen=new Set();
    for(let d=new Date(w[0]+'T12:00:00Z');d<=new Date(w[1]+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+1)){
      const day=d.toISOString().slice(0,10).replaceAll('-','');
      const url=`https://site.api.espn.com/apis/site/v2/sports/${C.sportPath}/scoreboard?dates=${day}&limit=1000`;
      const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('ESPN '+r.status+' on '+day);
      const p=await r.json();for(const ev of Array.isArray(p.events)?p.events:[]){if(!seen.has(String(ev.id))){seen.add(String(ev.id));out.push(ev);}}
    }
    return out;
  }
  function card(ev){
    const ts=teams(ev),a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1];
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${logo(t)?`<img src="${esc(logo(t))}" alt="" loading="lazy">`:''}<span>${esc(name(t))}</span></span><strong>${esc(t?.score??'—')}</strong></div>`;
    return `<a class="ghq-score-card" href="https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(ev.id)}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(fmt(ev.date))}</span><b>ESPN</b></div>${row(a)}${row(h)}<div class="ghq-score-status">${esc(status(ev))}</div></a>`;
  }
  function empty(rank,nm){return `<div class="ghq-score-card ghq-score-empty"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(nm)}</span></div><div class="ghq-score-status">NO MATCHUP FOUND IN ESPN FEED</div></div>`;}
  async function render(){
    const weekEl=$('fcs-week-filter'),top=$('fcs-top20'),big=$('bigsky-score-games'),st=$('fcs-status');if(!weekEl||!top||!big)return;
    if(!weekEl.dataset.ready){C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});weekEl.dataset.ready='1';}
    if(!weekEl.dataset.userChanged)weekEl.value=String(weekIndex());
    const w=C.weeks[Number(weekEl.value)||0];top.innerHTML='<div class="ghq-score-empty">Loading ESPN schedule…</div>';big.innerHTML='';if(st)st.textContent='Loading scores…';
    try{
      const [data,events]=await Promise.all([fetch('data.json?scoreboard='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data.json '+r.status);return r.json();}),fetchWeek(w)]);
      const rankings=(data.fcs_top25||data.fcs_top20||[]).slice(0,25);
      top.innerHTML=rankings.map((r,i)=>{const nm=r.team||r.name||'';const ev=events.find(e=>teams(e).some(t=>same(nm,name(t))));return ev?card(ev):empty(r.rank||i+1,nm);}).join('');
      const bs=events.filter(e=>teams(e).some(t=>C.bigSkyIds.has(id(t))));
      big.innerHTML=bs.length?bs.sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(card).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
      if(st)st.textContent=`Loaded ${events.length} ESPN events • ${w[2]}`;
    }catch(err){top.innerHTML='<div class="ghq-score-empty"><b>SCHEDULE DATA UNAVAILABLE</b><span>ESPN did not return the selected week.</span></div>';big.innerHTML='<div class="ghq-score-empty">SCHEDULE DATA UNAVAILABLE</div>';if(st)st.textContent='Schedule data unavailable';console.error('Griz scoreboard',err);}
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();
