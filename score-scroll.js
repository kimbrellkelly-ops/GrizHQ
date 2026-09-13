/* Griz HQ score scroll — single source of truth for the header strip. */
(function () {
  'use strict';
  if (window.__grizScoreScrollController) return;
  const games = document.getElementById('score-games');
  const groupSelect = document.getElementById('score-group-select');
  const weekSelect = document.getElementById('score-week-select');
  const previous = document.querySelector('.v2-score-prev');
  const next = document.querySelector('.v2-score-next');
  if (!games || !weekSelect) return;
  window.__grizScoreScrollController = true;

  const WEEKS = [
    ['2026-08-27','2026-08-30'], ['2026-09-03','2026-09-06'],
    ['2026-09-10','2026-09-13'], ['2026-09-17','2026-09-20'],
    ['2026-09-24','2026-09-27'], ['2026-10-01','2026-10-04'],
    ['2026-10-08','2026-10-11'], ['2026-10-15','2026-10-18'],
    ['2026-10-22','2026-10-25'], ['2026-10-29','2026-11-01'],
    ['2026-11-05','2026-11-08'], ['2026-11-12','2026-11-15'],
    ['2026-11-19','2026-11-22'], ['2026-11-26','2026-11-29'],
    ['2026-12-03','2026-12-06']
  ];
  const state = { index: 0, group: groupSelect ? groupSelect.value : 'fcs', data: null, request: 0 };
  const aliases = {
    montana:['montana','montanagrizzlies'], montanastate:['montanastate','montanastatebobcats'],
    idaho:['idaho','idahovandals'], weberstate:['weberstate','weberstatewildcats'],
    easternwashington:['easternwashington','easternwashingtoneagles'], northernarizona:['northernarizona','northernarizonalumberjacks'],
    northerncolorado:['northerncolorado','northerncoloradobears'], idahostate:['idahostate','idahostatebengals'],
    calpoly:['calpoly','calpolytechnic','calpolymustangs'], southernutah:['southernutah','southernutahthunderbirds'],
    utahtech:['utahtech','utahtechtrailblazers'], ucdavis:['ucdavis','ucdavisaggies'], portlandstate:['portlandstate','portlandstatevikings']
  };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean = s => String(s || '').replace(/\s*\([^)]*\)\s*$/, '').replace(/\s+/g, ' ').trim();
  const norm = s => clean(s).toLowerCase().replace(/[^a-z0-9]/g, '');
  const canonical = s => { const n = norm(s); return Object.keys(aliases).find(k => aliases[k].includes(n)) || null; };
  const sameTeam = (a,b) => { const na=norm(a), nb=norm(b), ca=canonical(a), cb=canonical(b); return !!na && !!nb && (na===nb || (ca && cb && ca===cb) || na.includes(nb) || nb.includes(na)); };
  const dateOnly = s => String(s || '').slice(0,10);
  const formatDate = s => new Date(s + 'T12:00:00Z').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
  const espnWeek = i => `https://www.espn.com/college-football/scoreboard/_/week/${i+1}/year/2026/seasontype/2`;
  const teamName = t => t?.shortDisplayName || t?.short || t?.displayName || t?.name || t?.abbreviation || 'Team';
  const logo = id => id ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id)}.png` : '';
  const currentIndex = () => { const today = new Date().toISOString().slice(0,10); const found = WEEKS.findIndex(w => today >= w[0] && today <= w[1]); return found >= 0 ? found : 0; };
  const allCachedEvents = data => Object.values(data?.fcs_scores || {}).flat().filter(Boolean);
  const eventFor = (events, away, home, date) => events.find(ev => { const ts=ev.teams || []; if(ts.length<2) return false; const a=ts.find(t=>t.homeAway==='away')||ts[0], h=ts.find(t=>t.homeAway==='home')||ts[1]; const ed=dateOnly(ev.date); return Math.abs((new Date(date)-new Date(ed))/86400000)<=1 && sameTeam(teamName(a),away) && sameTeam(teamName(h),home); });
  function message(title, detail, link) { const el=document.createElement(link?'a':'div'); el.className='v2-score-card v2-score-empty'; if(link){el.href=link;el.target='_blank';el.rel='noopener';} el.innerHTML=`<strong>${esc(title)}</strong><small>${esc(detail)}</small>`; games.replaceChildren(el); }
  function renderCard(item) {
    const ev=item.event, ts=ev?.teams || [], away=ts.find(t=>t.homeAway==='away') || ts[0], home=ts.find(t=>t.homeAway==='home') || ts[1];
    const awayName=away?teamName(away):item.away, homeName=home?teamName(home):item.home;
    const completed=!!ev?.completed, live=!!ev && !completed && ['in','halftime','endperiod','post'].includes(String(ev.state||'').toLowerCase());
    const status=completed?'FINAL':live?(ev.detail||'LIVE'):(ev?.detail||item.network||'Scheduled');
    const href=ev?.id?`https://www.espn.com/college-football/game/_/gameId/${ev.id}`:espnWeek(state.index);
    const el=document.createElement('a'); el.className='v2-score-card'+(canonical(awayName)==='montana'||canonical(homeName)==='montana'?' featured':''); el.href=href; el.target='_blank'; el.rel='noopener';
    el.innerHTML=`<div class="v2-score-meta"><span>${esc(item.dateLabel||formatDate(item.date))}</span><b>${esc(ev?.broadcasts?.[0]||item.network||'ESPN')}</b></div><div class="v2-score-status ${live?'is-live':''}">${esc(status)}</div><div class="v2-score-team"><span class="v2-score-team-name">${away?.id?`<img src="${logo(away.id)}" alt="" loading="lazy" decoding="async">`:''}<span>${esc(awayName)}</span></span><b>${esc(away?.score ?? '—')}</b></div><div class="v2-score-team"><span class="v2-score-team-name">${home?.id?`<img src="${logo(home.id)}" alt="" loading="lazy" decoding="async">`:''}<span>${esc(homeName)}</span></span><b>${esc(home?.score ?? '—')}</b></div><em>${ev?.id?'ESPN Gamecast ↗':'ESPN scoreboard ↗'}</em>`;
    return el;
  }
  function render() {
    const data=state.data; if(!data){message('Loading scores…','Checking the current score data');return;}
    const [from,to]=WEEKS[state.index], events=allCachedEvents(data), items=[];
    if(state.group==='fcs') {
      const ranked=(data.fcs_top25||data.fcs_top20||[]).map(x=>norm(x.team||x.name||x));
      events.forEach(ev=>{const d=dateOnly(ev.date), ts=ev.teams||[]; if(d<from||d>to||ts.length<2)return; const a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1]; const names=ts.map(t=>norm(teamName(t))); if(ranked.length && !names.some(n=>ranked.some(r=>n===r||n.includes(r)||r.includes(n))))return; items.push({date:d,dateLabel:formatDate(d),away:teamName(a),home:teamName(h),event:ev});});
    } else {
      (data.big_sky_full_schedules||[]).forEach(row=>{const raw=String(row.date||''), m=raw.match(/^(Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})/); if(!m)return; const date=`2026-${({Aug:'08',Sep:'09',Oct:'10',Nov:'11',Dec:'12'})[m[1]]}-${String(m[2]).padStart(2,'0')}`; if(date<from||date>to)return; const away=row.location==='Away'?row.team:row.opponent, home=row.location==='Away'?row.opponent:row.team; if(!away||!home)return; items.push({date,dateLabel:formatDate(date),away,home,network:row.network,event:eventFor(events,away,home,date)});});
    }
    items.sort((a,b)=>a.date.localeCompare(b.date));
    if(!items.length){message(`${state.group==='bigsky'?'Big Sky':'Top 25 FCS'} · Week ${state.index}`,'No local games found · Open ESPN scoreboard ↗',espnWeek(state.index));return;}
    games.replaceChildren(...items.map(renderCard)); games.scrollLeft=0;
  }
  async function load() { const token=++state.request; message('Loading scores…','Checking the current score data'); try { const r=await fetch(`data.json?scoreboard=${Date.now()}`,{cache:'no-store'}); if(!r.ok) throw new Error(`HTTP ${r.status}`); const data=await r.json(); if(token!==state.request)return; state.data=data; render(); } catch(err) { if(token!==state.request)return; message('Score data unavailable','Refresh the page or open ESPN below',espnWeek(state.index)); } }
  function setIndex(i){ state.index=Math.max(0,Math.min(WEEKS.length-1,i)); weekSelect.value=String(state.index); if(previous)previous.disabled=state.index===0; if(next)next.disabled=state.index===WEEKS.length-1; render(); }
  weekSelect.replaceChildren(...WEEKS.map((_,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=`Week ${i}`;return o;}));
  state.index=currentIndex(); weekSelect.value=String(state.index); setIndex(state.index);
  weekSelect.addEventListener('change',()=>{setIndex(Number(weekSelect.value)||0);});
  groupSelect?.addEventListener('change',()=>{state.group=groupSelect.value;load();});
  // The side arrows belong to the horizontal card scroller. They must never change weeks.
  // Week changes are controlled only by the week dropdown.
  load();
  window.setInterval(load, 60000);
})();
