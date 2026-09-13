/* Griz HQ header scoreboard: the only controller for the top score strip. */
(function () {
  'use strict';
  const boot = () => {
    if (window.__grizHeaderScoreController) return;
    const games = document.getElementById('score-games');
    const group = document.getElementById('score-group-select');
    const week = document.getElementById('score-week-select');
    const prev = document.querySelector('.v2-score-prev');
    const next = document.querySelector('.v2-score-next');
    if (!games || !group || !week) return;
    window.__grizHeaderScoreController = true;

    const WEEKS = [
      ['2026-08-27','2026-08-30'], ['2026-09-03','2026-09-06'], ['2026-09-10','2026-09-13'],
      ['2026-09-17','2026-09-20'], ['2026-09-24','2026-09-27'], ['2026-10-01','2026-10-04'],
      ['2026-10-08','2026-10-11'], ['2026-10-15','2026-10-18'], ['2026-10-22','2026-10-25'],
      ['2026-10-29','2026-11-01'], ['2026-11-05','2026-11-08'], ['2026-11-12','2026-11-15'],
      ['2026-11-19','2026-11-22'], ['2026-11-26','2026-11-29'], ['2026-12-03','2026-12-06']
    ];
    const MONTHS = {Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12'};
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const clean = v => String(v || '').replace(/\s*\([^)]*\)\s*$/, '').replace(/\s+/g, ' ').trim();
    const norm = v => clean(v).toLowerCase().replace(/[^a-z0-9]/g, '');
    const dateOnly = v => String(v || '').slice(0, 10);
    const dateLabel = v => new Date(v + 'T12:00:00Z').toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric'});
    const team = t => t?.shortDisplayName || t?.short || t?.displayName || t?.name || t?.abbreviation || 'Team';
    const ESPN_LOGOS = {
      calpoly:'13',
      easternwashington:'331',
      idaho:'70',
      montana:'149',
      montanastate:'147',
      weberstate:'2692',
      northernarizona:'246',
      northerncolorado:'2458',
      idahostate:'304',
      utahtech:'3101',
      ucdavis:'302',
      portlandstate:'250',
      southernutah:'253')
    };
    const logo = (id, name) => {
      const resolved = id || ESPN_LOGOS[canonical(name)] || '';
      return resolved ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(resolved)}.png` : '';
    };
    const aliases = {
      montana:['montana','montanagrizzlies'], montanastate:['montanastate','montanastatebobcats'],
      idaho:['idaho','idahovandals'], weberstate:['weberstate','weberstatewildcats'],
      easternwashington:['easternwashington','easternwashingtoneagles','easternwash','ewu','eagles'], northernarizona:['northernarizona','northernarizonalumberjacks'],
      northerncolorado:['northerncolorado','northerncoloradobears'], idahostate:['idahostate','idahostatebengals'],
      calpoly:['calpoly','calpolytechnic','calpolymustangs','calpolymustang','mustangs'], southernutah:['southernutah','southernutahthunderbirds'],
      utahtech:['utahtech','utahtechtrailblazers'], ucdavis:['ucdavis','ucdavisaggies'], portlandstate:['portlandstate','portlandstatevikings']
    };
    const canonical = value => { const n = norm(value); return Object.keys(aliases).find(k => aliases[k].includes(n)) || null; };
    const sameTeam = (a,b) => { const na=norm(a), nb=norm(b), ca=canonical(a), cb=canonical(b); return na===nb || (ca && cb && ca===cb) || na.includes(nb) || nb.includes(na); };
    const events = data => Object.values(data?.fcs_scores || {}).flat().filter(Boolean);
    const findEvent = (all, away, home, date) => all.find(ev => {
      const ts = ev.teams || []; if (ts.length < 2) return false;
      const a = ts.find(t => t.homeAway === 'away') || ts[0];
      const h = ts.find(t => t.homeAway === 'home') || ts[1];
      const eventName = norm(ev.name || '');
      const pairMatch = sameTeam(team(a), away) && sameTeam(team(h), home);
      const nameMatch = eventName.includes(norm(away)) && eventName.includes(norm(home));
      return Math.abs((new Date(date)-new Date(dateOnly(ev.date))) / 86400000) <= 1 && (pairMatch || nameMatch);
    });
    const espn = i => `https://www.espn.com/college-football/scoreboard/_/week/${i+1}/year/2026/seasontype/2`;
    const show = (title, detail, link) => {
      const el = document.createElement(link ? 'a' : 'div'); el.className='v2-score-card v2-score-empty';
      if (link) { el.href=link; el.target='_blank'; el.rel='noopener'; }
      el.innerHTML=`<strong>${esc(title)}</strong><small>${esc(detail)}</small>`; games.replaceChildren(el);
    };
    const card = item => {
      const ev=item.event, ts=ev?.teams || [], away=ts.find(t=>t.homeAway==='away') || ts[0], home=ts.find(t=>t.homeAway==='home') || ts[1];
      const awayName=away ? team(away) : item.away, homeName=home ? team(home) : item.home;
      const completed=!!ev?.completed, live=!!ev && !completed && ['in','halftime','endperiod','post'].includes(String(ev.state||'').toLowerCase());
      const status=completed?'FINAL':live?(ev.detail||'LIVE'):(ev?.detail||item.network||'SCHEDULED');
      const a=document.createElement('a'); a.className='v2-score-card'+(canonical(awayName)==='montana'||canonical(homeName)==='montana'?' featured':'');
      a.href=ev?.id?`https://www.espn.com/college-football/game/_/gameId/${ev.id}`:espn(state.index); a.target='_blank'; a.rel='noopener';
      a.innerHTML=`<div class="v2-score-meta"><span>${esc(item.dateLabel)}</span><b>${esc(ev?.broadcasts?.[0]||item.network||'ESPN')}</b></div><div class="v2-score-status ${live?'is-live':''}">${esc(status)}</div><div class="v2-score-team"><span class="v2-score-team-name">${(away?.id||logo('',awayName))?`<img src="${logo(away?.id,awayName)}" alt="" loading="lazy" decoding="async">`:''}<span>${esc(awayName)}</span></span><b>${esc(away?.score ?? '—')}</b></div><div class="v2-score-team"><span class="v2-score-team-name">${(home?.id||logo('',homeName))?`<img src="${logo(home?.id,homeName)}" alt="" loading="lazy" decoding="async">`:''}<span>${esc(homeName)}</span></span><b>${esc(home?.score ?? '—')}</b></div>`;
      return a;
    };
    const state={index:0,group:group.value||'fcs',data:null,request:0};
    function render(){
      if(!state.data){show('Loading scores…','Checking current score data');return;}
      const [from,to]=WEEKS[state.index], all=events(state.data), items=[];
      if(state.group==='fcs'){
        const ranked=(state.data.fcs_top25||state.data.fcs_top20||[]).map(x=>norm(x.team||x.name||x));
        all.forEach(ev=>{const d=dateOnly(ev.date),ts=ev.teams||[];if(d<from||d>to||ts.length<2)return;const a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1],names=ts.map(team).map(norm);if(ranked.length&&!names.some(n=>ranked.some(r=>n===r||n.includes(r)||r.includes(n))))return;items.push({date:d,dateLabel:dateLabel(d),away:team(a),home:team(h),event:ev});});
      } else {
        const seen=new Set();
        (state.data.big_sky_full_schedules||[]).forEach(row=>{
          const m=String(row.date||'').match(/^(Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})/); if(!m)return;
          const d=`2026-${MONTHS[m[1]]}-${String(m[2]).padStart(2,'0')}`; if(d<from||d>to)return;
          const away=row.location==='Away'?row.team:row.opponent, home=row.location==='Away'?row.opponent:row.team; if(!away||!home)return;
          const key=`${d}|${[norm(away),norm(home)].sort().join('|')}`; if(seen.has(key))return; seen.add(key);
          items.push({date:d,dateLabel:dateLabel(d),away,home,network:row.network,event:findEvent(all,away,home,d)});
        });
      }
      items.sort((a,b)=>a.date.localeCompare(b.date));
      if(!items.length){show(`${state.group==='bigsky'?'Big Sky':'Top 25 FCS'} · Week ${state.index}`,'No games found · Open ESPN scoreboard ↗',espn(state.index));}
      else games.replaceChildren(...items.map(card));
      games.scrollLeft=0; updateArrows();
    }
    async function load(){const token=++state.request;show('Loading scores…','Checking current score data');try{const r=await fetch(`data.json?scoreboard=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw Error(r.status);state.data=await r.json();if(token===state.request)render();}catch(e){if(token===state.request)show('Score data unavailable','Refresh the page or open ESPN below',espn(state.index));}}
    function setWeek(i){state.index=Math.max(0,Math.min(WEEKS.length-1,i));week.value=String(state.index);render();}
    function updateArrows(){const max=Math.max(0,games.scrollWidth-games.clientWidth);prev.disabled=games.scrollLeft<=2;next.disabled=games.scrollLeft>=max-2;}
    week.replaceChildren(...WEEKS.map((_,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=`Week ${i}`;return o;}));
    const today=new Date().toISOString().slice(0,10);state.index=Math.max(0,WEEKS.findIndex(w=>today>=w[0]&&today<=w[1]));week.value=String(state.index);
    week.addEventListener('change',()=>setWeek(Number(week.value)||0));
    group.addEventListener('change',()=>{state.group=group.value;load();});
    prev.addEventListener('click',()=>games.scrollBy({left:-Math.max(260,Math.floor(games.clientWidth*.8)),behavior:'smooth'}));
    next.addEventListener('click',()=>games.scrollBy({left:Math.max(260,Math.floor(games.clientWidth*.8)),behavior:'smooth'}));
    games.addEventListener('scroll',updateArrows,{passive:true}); window.addEventListener('resize',updateArrows);
    if(window.ResizeObserver)new ResizeObserver(updateArrows).observe(games);
    load(); window.setInterval(load,60000);
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
