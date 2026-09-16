/* Griz HQ scoreboard — clean, independent renderer. */
(function(){
  'use strict';
  const C=window.GRIZ_SCOREBOARD_CONFIG;
  if(!C) return;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();
  const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,'');
  const aliases={southdakotastate:['southdakotastate','southdakotastatejackrabbits'],southdakota:['southdakota','southdakotacoyotes'],montanastate:['montanastate','montanastatebobcats'],montana:['montana','montanagrizzlies']};
  const same=(a,b)=>{const x=norm(a),y=norm(b);if(!x||!y)return false;if(x===y||x.includes(y)||y.includes(x))return true;return Object.values(aliases).some(v=>v.includes(x)&&v.includes(y));};
  const name=c=>c?.team?.displayName||c?.team?.shortDisplayName||c?.team?.name||c?.displayName||c?.name||'Team';
  const id=c=>String(c?.team?.id||c?.id||'');
  const logo=c=>c?.team?.logo||c?.logo||(id(c)?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id(c))}.png`:'');
  const comps=ev=>ev?.competitions?.[0];
  const teams=ev=>comps(ev)?.competitors||[];
  const status=ev=>{const s=comps(ev)?.status?.type||{};if(s.completed)return 'FINAL';if(s.state==='in'||s.name==='STATUS_IN_PROGRESS')return s.shortDetail||'LIVE';return s.shortDetail||s.detail||'SCHEDULED';};
  const dateKey=s=>String(s||'').slice(0,10);
  const fmt=s=>new Date(s+'T12:00:00Z').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  const weekIndex=()=>{const k=new Date().toISOString().slice(0,10);let i=C.weeks.findIndex(w=>k>=w[0]&&k<=w[1]);return i<0?0:i;};
  async function fetchWeek(w){
    const events=[],seen=new Set();
    for(let d=new Date(w[0]+'T12:00:00Z');d<=new Date(w[1]+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+1)){
      const day=d.toISOString().slice(0,10).replaceAll('-','');
      let got=false;
      for(const host of ['https://site.api.espn.com','https://site.web.api.espn.com']){
        try{const r=await fetch(`${host}/apis/site/v2/sports/${C.sportPath}/scoreboard?dates=${day}&limit=1000`,{cache:'no-store'});if(!r.ok)continue;const p=await r.json();if(!Array.isArray(p.events))continue;for(const ev of p.events){if(!seen.has(String(ev.id))){seen.add(String(ev.id));events.push(ev)}}got=true;break;}catch(e){}
      }
      if(!got) throw new Error('ESPN schedule request failed for '+day);
    }
    return events;
  }
  function card(ev,rankedName,rank){
    const ts=teams(ev),a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1];
    const row=t=>`<div class="ghq-score-team"><span class="ghq-score-team-name">${logo(t)?`<img src="${esc(logo(t))}" alt="" loading="lazy" decoding="async">`:''}<span>${esc(name(t))}</span></span><strong>${esc(t?.score??'—')}</strong></div>`;
    return `<a class="ghq-score-card" href="https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(ev.id)}" target="_blank" rel="noopener"><div class="ghq-score-meta"><span>${esc(fmt(dateKey(ev.date)))}</span><b>ESPN</b></div>${row(a)}${row(h)}<div class="ghq-score-status">${esc(status(ev))}</div></a>`;
  }
  function empty(rank,nameText,reason){return `<div class="ghq-score-card ghq-score-empty"><div class="ghq-score-meta"><b>#${esc(rank)}</b><span>${esc(nameText)}</span></div><div class="ghq-score-status">${esc(reason)}</div></div>`;}
  function render(data,events,w){
    const top=$('fcs-top20'),big=$('bigsky-score-games'),statusEl=$('fcs-status');
    const rankings=(data.fcs_top25||data.fcs_top20||[]).slice(0,25);
    const rankedEvents=rankings.map((r,i)=>{const nm=r.team||r.name||'';return {r,nm,rank:r.rank||i+1,ev:events.find(ev=>teams(ev).some(t=>same(nm,name(t))))};});
    top.innerHTML=rankedEvents.map(x=>x.ev?card(x.ev,x.nm,x.rank):empty(x.rank,x.nm,'BYE / NO GAME THIS WEEK')).join('');
    const bs=events.filter(ev=>teams(ev).some(t=>C.bigSkyIds.has(id(t))));
    big.innerHTML=bs.length?bs.sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(ev=>card(ev,'', '')).join(''):'<div class="ghq-score-empty">NO BIG SKY GAMES THIS WEEK</div>';
    if(statusEl)statusEl.textContent=`Loaded ${events.length} ESPN events • ${w[2]}`;
  }
  async function render(){
    const weekEl=$('fcs-week-filter');if(!weekEl)return;
    if(!weekEl.dataset.ghqReady){C.weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o)});weekEl.dataset.ghqReady='1';}
    if(!weekEl.dataset.userChanged)weekEl.value=String(weekIndex());
    const w=C.weeks[Number(weekEl.value)||0],top=$('fcs-top20'),big=$('bigsky-score-games');
    if(top)top.innerHTML='<div class="ghq-score-empty">Loading verified ESPN schedule…</div>';
    if(big)big.innerHTML='';
    try{const [data,events]=await Promise.all([fetch('data.json?scoreboard='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('data.json unavailable');return r.json()}),fetchWeek(w)]);render(data,events,w);}
    catch(e){if(top)top.innerHTML='<div class="ghq-score-empty"><b>SCHEDULE DATA UNAVAILABLE</b><span>ESPN did not return a complete week. No false byes are shown.</span></div>';if(big)big.innerHTML='<div class="ghq-score-empty">SCHEDULE DATA UNAVAILABLE</div>';const s=$('fcs-status');if(s)s.textContent='Schedule data unavailable';console.warn('Griz scoreboard:',e);}
  }
  window.GrizScoreboard={render};
  const week=$('fcs-week-filter');if(week)week.addEventListener('change',()=>{week.dataset.userChanged='1';render();});
  render();
})();
