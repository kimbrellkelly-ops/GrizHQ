async function loadGrizData() {
  try {
    const res = await fetch("data.json?ts=" + Date.now(), {cache: "no-store"});
    const d = await res.json();

    const next = d.next_game || {};
    const dateEl = document.getElementById("next-game-date");
    const venueEl = document.getElementById("next-game-venue");
    const oppEl = document.getElementById("next-opponent-name");
    const srcEl = document.getElementById("opponent-source");
    if (dateEl) dateEl.textContent = [next.date, next.time].filter(Boolean).join(" • ").toUpperCase();
    if (venueEl) venueEl.innerHTML = (next.venue || "Washington-Grizzly Stadium, Missoula, Mont.").replace(", ", "<br>");
    if (oppEl) oppEl.textContent = (next.opponent || "Opponent").toUpperCase();
    const nextOppLogo = document.getElementById("next-opponent-logo");
    if (nextOppLogo) {
      const nextLogos = {
        "Southern Utah": "https://a.espncdn.com/i/teamlogos/ncaa/500/253.png",
        "Drake": "https://a.espncdn.com/i/teamlogos/ncaa/500/2181.png",
        "Utah Tech": "https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png",
        "Oregon State": "https://a.espncdn.com/i/teamlogos/ncaa/500/204.png",
        "UC Davis": "https://a.espncdn.com/i/teamlogos/ncaa/500/302.png",
        "Northern Colorado": "https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png",
        "Northern Arizona": "https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png",
        "Idaho": "https://a.espncdn.com/i/teamlogos/ncaa/500/70.png",
        "Eastern Washington": "https://a.espncdn.com/i/teamlogos/ncaa/500/331.png",
        "Portland State": "https://a.espncdn.com/i/teamlogos/ncaa/500/279.png",
        "Idaho State": "https://a.espncdn.com/i/teamlogos/ncaa/500/304.png",
        "Montana State": "https://a.espncdn.com/i/teamlogos/ncaa/500/147.png"
      };
      const logo = nextLogos[next.opponent];
      if (logo) { nextOppLogo.src = logo; nextOppLogo.alt = `${next.opponent} logo`; }
    }
    if (srcEl && next.url) { srcEl.href = next.url; srcEl.textContent = "Opponent information ↗"; }

    // Keep the compact header game bar synchronized with the same next-game data.
    const hgKicker = document.getElementById("header-gamebar-kicker");
    const hgOpp = document.getElementById("header-gamebar-opponent");
    const hgLogo = document.getElementById("header-gamebar-opponent-logo");
    const hgDate = document.getElementById("header-gamebar-date");
    const hgVenue = document.getElementById("header-gamebar-venue");
    if (hgKicker) hgKicker.textContent = "NEXT GAME";
    const opponentName = next.opponent || "OPPONENT";
    if (hgOpp) hgOpp.textContent = opponentName.toUpperCase();
    if (hgLogo) {
      const opponentLogos = {
        "Southern Utah": "https://a.espncdn.com/i/teamlogos/ncaa/500/253.png",
        "Drake": "https://a.espncdn.com/i/teamlogos/ncaa/500/2181.png",
        "Utah Tech": "https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png",
        "Oregon State": "https://a.espncdn.com/i/teamlogos/ncaa/500/204.png",
        "UC Davis": "https://a.espncdn.com/i/teamlogos/ncaa/500/302.png",
        "Northern Colorado": "https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png",
        "Northern Arizona": "https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png",
        "Idaho": "https://a.espncdn.com/i/teamlogos/ncaa/500/70.png",
        "Eastern Washington": "https://a.espncdn.com/i/teamlogos/ncaa/500/331.png",
        "Portland State": "https://a.espncdn.com/i/teamlogos/ncaa/500/279.png",
        "Idaho State": "https://a.espncdn.com/i/teamlogos/ncaa/500/304.png",
        "Montana State": "https://a.espncdn.com/i/teamlogos/ncaa/500/147.png"
      };
      const logo = opponentLogos[opponentName];
      if (logo) {
        hgLogo.src = logo;
        hgLogo.alt = `${opponentName} logo`;
      }
    }
    if (hgDate) hgDate.textContent = [next.date, next.time].filter(Boolean).join(" • ").toUpperCase();
    if (hgVenue) hgVenue.textContent = String(next.venue || "WASHINGTON-GRIZZLY STADIUM").split(",")[0].toUpperCase();

    const stats = document.getElementById("season-stats");
    if (stats && d.team) {
      const vals = [
        [d.team.record || "—","RECORD"],
        [d.team.conference_record || "—","BIG SKY"],
        [d.team.ppg || "—","PPG"],
        [d.team.opp_ppg || "—","OPP PPG"]
      ];
      stats.innerHTML = vals.map(x => `<div><b>${x[0]}</b><small>${x[1]}</small></div>`).join("");
    }

    const schedule = document.getElementById("schedule-list");
    if (schedule && Array.isArray(d.schedule)) {
      schedule.innerHTML = `<div class="schedule-row head"><span>DATE</span><span>OPPONENT</span><span>RESULT / TIME</span></div>` +
        d.schedule.map((g, i) => {
          const isNext = !g.result && i === d.schedule.findIndex(x => !x.result);
          return `<div class="schedule-row ${isNext ? "next" : ""}">
            <span>${g.date || ""}</span><b>${g.location === "Away" ? "@ " : ""}${g.opponent || ""}</b>
            <strong>${g.result || g.time || ""}</strong>
          </div>`;
        }).join("");
    }

    renderStatsDashboard(d.stats);

    renderPoll("coaches-poll", d.coaches_poll);
    renderPoll("media-poll", d.media_poll);
    renderMiniPolls(d.coaches_poll, d.media_poll);

    const rankDate = document.getElementById("rankings-date");
    if (rankDate) rankDate.textContent = d.rankings_date || "Updated weekly";
    const updated = document.getElementById("data-updated");
    if (updated) updated.textContent = d.updated ? "DATA UPDATED " + new Date(d.updated).toLocaleString([], {month:"short",day:"numeric",hour:"numeric",minute:"2-digit"}) : "";

    if (Array.isArray(d.news) && d.news.length) {
      const news = document.querySelectorAll("#news .auto-news");
      d.news.slice(0, 3).forEach((item, i) => {
        if (!news[i]) return;
        const title = news[i].querySelector("h3"), small = news[i].querySelector("small"), p = news[i].querySelector("p");
        if (title) title.innerHTML = `<a href="${item.url}" target="_blank" rel="noopener">${escapeHtml(item.title)}</a>`;
        if (small) small.textContent = item.date || "";
        if (p) p.textContent = item.description || "Latest Montana football news.";
      });
    }
  } catch (e) {
    console.warn("Griz HQ data layer unavailable; using page fallback.", e);
  }
}
function renderPoll(id, teams) {
  const el = document.getElementById(id);
  if (!el || !Array.isArray(teams)) return;
  el.innerHTML = teams.slice(0,20).map(t => `<li class="${String(t).toLowerCase().includes("montana") && !String(t).toLowerCase().includes("state") ? "griz" : ""}">${escapeHtml(t)}</li>`).join("");
}
function renderMiniPolls(coaches, media) {
  const wrap = document.getElementById("rankings-mini");
  if (!wrap || !Array.isArray(coaches) || !Array.isArray(media)) return;
  wrap.innerHTML = [coaches, media].map(poll => `<ol>${poll.slice(0,10).map(t => `<li class="${String(t).toLowerCase().includes("montana") && !String(t).toLowerCase().includes("state") ? "griz" : ""}">${escapeHtml(t)}</li>`).join("")}</ol>`).join("");
}
function escapeHtml(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
loadGrizData();

function renderDepthChart(d) {
  const dc = d.depth_chart;
  if (!dc) return;
  const note = document.getElementById("depth-chart-note");
  const updated = document.getElementById("depth-chart-updated");
  if (note) note.innerHTML = `${escapeHtml(dc.note || "Latest published two-deep")} <a href="${dc.source_url}" target="_blank" rel="noopener">Source ↗</a>`;
  if (updated) updated.textContent = dc.published ? `Published ${dc.published}` : "2026 season";
  ["offense","defense","special_teams"].forEach(section => {
    const el = document.getElementById("depth-" + (section === "special_teams" ? "special" : section));
    if (!el || !Array.isArray(dc[section])) return;
    el.innerHTML = `<div class="depth-head"><span>POS</span><span>1ST TEAM</span><span>2ND TEAM</span></div>` +
      dc[section].map(r => `<div class="depth-row"><b>${escapeHtml(r.position)}</b><span>${escapeHtml(r.first)}</span><span>${escapeHtml(r.second || "—")}${r.also ? `<small>Also: ${escapeHtml(r.also)}</small>` : ""}</span></div>`).join("");
  });
}
const _loadGrizDataOriginal = loadGrizData;
loadGrizData = async function() {
  await _loadGrizDataOriginal();
  try {
    const res = await fetch("data.json?ts=" + Date.now(), {cache:"no-store"});
    const d = await res.json();
    renderDepthChart(d);
  } catch(e) {}
};
loadGrizData();

async function renderBigSkyAndOpponent(){
  try {
    const d = await (await fetch("data.json?ts=" + Date.now(), {cache:"no-store"})).json();
    const table = document.getElementById("bigsky-table");
    const teamSelect = document.getElementById("bigsky-team-filter");
    const weekSelect = document.getElementById("bigsky-date-filter");
    const games = Array.isArray(d.big_sky_full_schedules) ? d.big_sky_full_schedules : [];
    const teams = Array.isArray(d.big_sky_teams) ? d.big_sky_teams : [];
    const weeks = [
      ["Aug 29","Aug 28–29"],["Sep 5","Sep 3–5"],["Sep 12","Sep 12"],["Sep 19","Sep 18–19"],
      ["Sep 26","Sep 26"],["Oct 3","Oct 2–3"],["Oct 10","Oct 10"],["Oct 17","Oct 17"],
      ["Oct 24","Oct 24"],["Oct 31","Oct 31"],["Nov 7","Nov 7"],["Nov 14","Nov 13–14"],["Nov 21","Nov 21"]
    ];
    const monthNum = {Aug:8, Sep:9, Oct:10, Nov:11};
    const dateObj = label => {
      const [m, day] = label.split(" ");
      return new Date(2026, monthNum[m]-1, Number(day), 12, 0, 0);
    };
    const weekForDate = label => {
      const dt = dateObj(label);
      const saturday = new Date(dt);
      saturday.setDate(dt.getDate() + (6 - dt.getDay()));
      return saturday.toLocaleDateString("en-US", {month:"short", day:"numeric"});
    };

    if (table && games.length) {
      if (teamSelect && !teamSelect.dataset.ready) {
        teams.forEach(team => {
          const opt = document.createElement("option");
          opt.value = team; opt.textContent = team.toUpperCase();
          teamSelect.appendChild(opt);
        });
        teamSelect.dataset.ready = "1";
      }
      if (weekSelect && !weekSelect.dataset.ready) {
        weeks.forEach(([value,label]) => {
          const opt = document.createElement("option");
          opt.value = value; opt.textContent = label;
          weekSelect.appendChild(opt);
        });
        weekSelect.dataset.ready = "1";
      }

      const today = new Date();
      const saturday = new Date(today);
      saturday.setDate(today.getDate() + (6 - today.getDay()));
      const currentWeek = saturday.toLocaleDateString("en-US", {month:"short", day:"numeric"});
      if (weekSelect) weekSelect.value = weeks.some(w => w[0] === currentWeek) ? currentWeek : weeks[0][0];

      function draw() {
        const selectedWeek = weekSelect?.value || weeks[0][0];
        const selectedTeam = teamSelect?.value || "ALL";
        const weekGames = games.filter(game => weekForDate(game.date) === selectedWeek);
        const shownTeams = selectedTeam === "ALL" ? teams : [selectedTeam];
        const rows = [];

        // Always walk every Big Sky team. The opponent can be Big Sky or non-conference.
        shownTeams.forEach(team => {
          const teamGames = weekGames.filter(game => game.team === team);
          if (!teamGames.length) {
            rows.push(`<div class="bigsky-row bye-row"><span>${escapeHtml(selectedWeek)}</span><b>${escapeHtml(team)}</b><span>BYE / NO GAME</span><span>—</span></div>`);
            return;
          }
          teamGames.sort((a,b) => dateObj(a.date) - dateObj(b.date));
          teamGames.forEach(game => {
            const prefix = game.location === "Away" ? "@ " : "vs ";
            const tag = game.big_sky_game ? ' <small class="league-tag">BIG SKY</small>' : ' <small class="league-tag nonconf-tag">NON-CONFERENCE</small>';
            rows.push(`<div class="bigsky-row"><span>${escapeHtml(game.date)}</span><b>${escapeHtml(team)}</b><span>${prefix}${escapeHtml(game.opponent)}${tag}</span><span>${escapeHtml(game.time || "TBA")}</span></div>`);
          });
        });

        table.innerHTML = `<div class="bigsky-row bigsky-head"><span>DATE</span><span>BIG SKY TEAM</span><span>OPPONENT</span><span>TIME</span></div>${rows.join("")}`;
      }
      if (teamSelect) teamSelect.onchange = draw;
      if (weekSelect) weekSelect.onchange = draw;
      draw();
    } else if (table) {
      table.innerHTML = '<div class="bigsky-empty"><b>Schedule data unavailable.</b><span>Try refreshing the page.</span></div>';
    }

    const opponent = d.next_game?.opponent || "Drake";

    // Keep the Game Center focused on Montana's NEXT game, not the game just played.
    const gameCenterTitle = document.getElementById("game-center-title");
    const gameCenterMeta = document.getElementById("game-center-meta");
    if (gameCenterTitle) {
      gameCenterTitle.textContent = `${opponent} at Montana`;
    }
    if (gameCenterMeta) {
      const nextDate = d.next_game?.date || "";
      const nextTime = d.next_game?.time || "";
      const nextVenue = String(d.next_game?.venue || "Washington-Grizzly Stadium").split(",")[0];
      gameCenterMeta.textContent = [nextDate, nextTime, nextVenue].filter(Boolean).join(" • ");
    }

    const resources = d.opponent_resources?.[opponent];
    if (resources) {
      const hub = document.getElementById("opponent-hub-name");
      const title = document.getElementById("opp-title");
      const official = document.getElementById("opp-official");
      const forum = document.getElementById("opp-forum");
      const forumLabel = document.getElementById("opp-forum-label");
      const media = document.getElementById("opp-media");
      if (hub) hub.textContent = opponent;
      if (title) title.textContent = opponent.toUpperCase();
      if (official) official.href = resources.official;
      if (forum) forum.href = resources.forum;
      if (forumLabel) forumLabel.textContent = resources.label || "Fan discussion";
      if (media) media.href = resources.media;
    }
  } catch (e) { console.warn("Big Sky render error", e); }
}
renderBigSkyAndOpponent();


async function renderFCSScoreboard(){
  const topEl=document.getElementById('fcs-top20');
  const bigSkyEl=document.getElementById('bigsky-score-games');
  const bigSkyLabelEl=document.getElementById('bigsky-score-label');
  const weekEl=document.getElementById('fcs-week-filter');
  const statusEl=document.getElementById('fcs-status');
  const refreshEl=document.getElementById('fcs-refresh');
  if(!topEl || !weekEl) return;

  const bigSkyTeams=['Montana','Montana State','Idaho','Weber State','Eastern Washington','Northern Arizona','Northern Colorado','Idaho State','Cal Poly','Southern Utah','Utah Tech','UC Davis','Portland State'];
  const weeks=[
    ['2026-08-27','2026-08-30','WEEK 0 • AUG 27–30'],['2026-09-03','2026-09-06','WEEK 1 • SEP 3–6'],['2026-09-10','2026-09-13','WEEK 2 • SEP 10–13'],['2026-09-17','2026-09-20','WEEK 3 • SEP 17–20'],['2026-09-24','2026-09-27','WEEK 4 • SEP 24–27'],['2026-10-01','2026-10-04','WEEK 5 • OCT 1–4'],['2026-10-08','2026-10-11','WEEK 6 • OCT 8–11'],['2026-10-15','2026-10-18','WEEK 7 • OCT 15–18'],['2026-10-22','2026-10-25','WEEK 8 • OCT 22–25'],['2026-10-29','2026-11-01','WEEK 9 • OCT 29–NOV 1'],['2026-11-05','2026-11-08','WEEK 10 • NOV 5–8'],['2026-11-12','2026-11-15','WEEK 11 • NOV 12–15'],['2026-11-19','2026-11-22','WEEK 12 • NOV 19–22']
  ];
  if(!weekEl.dataset.ready){weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});weekEl.dataset.ready='1';}
  const now=new Date(); let current=weeks.findIndex(w=>now>=new Date(w[0]+'T00:00:00')&&now<=new Date(w[1]+'T23:59:59')); if(current<0) current=0;
  if(!weekEl.dataset.userChanged) weekEl.value=String(current);

  let localData={};
  try{localData=await (await fetch('data.json?ts='+Date.now(),{cache:'no-store'})).json();}catch(e){
    statusEl.textContent='Score data unavailable';
    return;
  }

  const top25=Array.isArray(localData.fcs_top25)?localData.fcs_top25:(Array.isArray(localData.fcs_top20)?localData.fcs_top20:[]);
  const cachedScores=localData.fcs_scores || {};
  const rankDate=document.getElementById('fcs-rankings-date');
  if(rankDate&&localData.fcs_rankings_date) rankDate.textContent='Stats Perform • '+localData.fcs_rankings_date;

  function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');}
  const teamAliases={
    'montana':['montana','montanagrizzlies'],
    'montanastate':['montanastate','montanast','montanastatebobcats'],
    'idaho':['idaho','idahovandals'],
    'weberstate':['weberstate','weberst','weberstatewildcats'],
    'easternwashington':['easternwashington','ewashington','easternwash','easternwashingtoneagles'],
    'northernarizona':['northernarizona','narizona','northernaz','northernarizonalumberjacks'],
    'northerncolorado':['northerncolorado','ncolorado','northerncoloradobears'],
    'idahostate':['idahostate','idst','idahostatebengals'],
    'calpoly':['calpoly','calpolytechnic','calpolymustangs'],
    'southernutah':['southernutah','southeasternutah','soutah','soututah','southernutahthunderbirds'],
    'utahtech':['utahtech','utahtechuniversity','utahtechtrailblazers'],
    'ucdavis':['ucdavis','ucdavisaggies'],
    'portlandstate':['portlandstate','portlandst','portlandstatevikings']
  };
  function teamMatches(name,team){
    const n=norm(name), t=norm(team);
    if(n===t) return true;
    for(const variants of Object.values(teamAliases)){
      if(variants.includes(n) && variants.includes(t)) return true;
    }
    return false;
  }
  function findTeamEvent(name,events){
    return events.find(ev=>(ev.teams||[]).some(t=>teamMatches(name,t.name)||teamMatches(name,t.short)))||null;
  }
  function statusText(ev){
    if(!ev)return 'NO GAME';
    if(ev.completed)return ev.detail||'FINAL';
    if(ev.state==='in')return ev.detail||'LIVE';
    return ev.date?new Date(ev.date).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'TBA';
  }
  function gameLabel(ev){
    const teams=ev?.teams||[];
    const away=teams.find(x=>x.homeAway==='away'),home=teams.find(x=>x.homeAway==='home');
    return {away:away?.short||away?.name||'Away',home:home?.short||home?.name||'Home',time:statusText(ev)};
  }
  function scoreLine(ev,name){
    if(!ev)return '<small>NO GAME</small>';
    const me=(ev.teams||[]).find(x=>teamMatches(name,x.name)||teamMatches(name,x.short));
    if(!me)return '<small>'+escapeHtml(statusText(ev))+'</small>';
    const other=(ev.teams||[]).find(x=>x!==me);
    if(ev.completed||ev.state==='in'){const other=(ev.teams||[]).find(x=>x!==me);return `<span class="score-big">${escapeHtml(me.score??'0')}–${escapeHtml(other?.score??'0')}</span><small>${escapeHtml(statusText(ev))}</small>`;}
    return `<small>${escapeHtml(statusText(ev))}</small>`;
  }

  function eventsForWeek(w){
    const out=[];
    Object.entries(cachedScores).forEach(([date,items])=>{
      if(date>=w[0]&&date<=w[1]&&Array.isArray(items)) out.push(...items);
    });
    const seen=new Set();
    return out.filter(ev=>{if(seen.has(ev.id))return false;seen.add(ev.id);return true;});
  }

  async function draw(){
    const w=weeks[Number(weekEl.value)||0];
    statusEl.textContent='Loading cached scores…';
    topEl.innerHTML='<div class="fcs-loading">Loading Top 25…</div>';
    if(bigSkyEl)bigSkyEl.innerHTML='<div class="fcs-loading">Loading Big Sky games…</div>';
    if(bigSkyLabelEl)bigSkyLabelEl.textContent=w[2]+' • All 13 teams';
    const events=eventsForWeek(w);
    statusEl.textContent=`${events.length} FCS games • cached feed`;

    topEl.innerHTML=top25.slice(0,25).map(t=>{
      const ev=findTeamEvent(t.team,events);
      const isGriz=norm(t.team)==='montana';
      const isBigSky=bigSkyTeams.includes(t.team);
      const detail=ev?gameLabel(ev):null;
      const matchup=detail?`${escapeHtml(detail.away)} @ ${escapeHtml(detail.home)}`:'No game this week';
      const cardClass=isGriz?'griz':(isBigSky?'bigsky':'');
      return `<div class="fcs-rank-card ${cardClass}"><span class="fcs-rank">${escapeHtml(t.rank)}</span><div class="fcs-rank-team"><b>${escapeHtml(t.team)}</b><small>${escapeHtml(t.record||'')} • ${matchup}</small></div><span class="fcs-rank-score">${scoreLine(ev,t.team)}</span></div>`;
    }).join('');

    if(bigSkyEl){
      bigSkyEl.innerHTML=bigSkyTeams.map(team=>{
        const ev=findTeamEvent(team,events);
        if(!ev)return `<div class="fcs-game scheduled bigsky-row bye"><div class="fcs-time">BYE</div><div class="fcs-matchup"><b>${escapeHtml(team)}</b><small>NO GAME THIS WEEK</small></div><div class="fcs-score">BYE</div><div class="fcs-tv"></div></div>`;
        const d=gameLabel(ev);
        const label=(team==='Weber State'&&[d.away,d.home].includes('Southern Utah'))||(team==='Southern Utah'&&[d.away,d.home].includes('Weber State'))?'NON-CONFERENCE':'BIG SKY';
        const scores=(ev.teams||[]).map(x=>`${escapeHtml(x.short||x.name||'')} ${escapeHtml(x.score??'')}`).join(' • ');
        const tv=(ev.broadcasts||[]).slice(0,2).join(', ');
        const state=ev.state==='in'?'live':(ev.completed?'final':'scheduled');
        const rightScore=(ev.completed||ev.state==='in') ? (()=>{ const a=(ev.teams||[]).find(x=>x.homeAway==='away'), h=(ev.teams||[]).find(x=>x.homeAway==='home'); return `<span class="score-big">${escapeHtml(a?.score??'0')}–${escapeHtml(h?.score??'0')}</span><small>${escapeHtml(statusText(ev))}</small>`; })() : `<small>${escapeHtml(statusText(ev))}</small>`;
        return `<div class="fcs-game ${state} bigsky-row"><div class="fcs-time">${escapeHtml(d.time)}</div><div class="fcs-matchup"><b>${escapeHtml(d.away)} @ ${escapeHtml(d.home)}</b><small>${scores} <span class="bigsky-game-tag">${label}</span></small></div><div class="fcs-score">${rightScore}</div><div class="fcs-tv">${escapeHtml(tv)}</div></div>`;
      }).join('');
    }
  }
  weekEl.onchange=()=>{weekEl.dataset.userChanged='1';draw();};
  if(refreshEl)refreshEl.onclick=draw;
  draw();
  setInterval(()=>{if(new Date().getDay()>=4)draw();},60000);
}

renderFCSScoreboard();

/* Griz HQ tab navigation */
(function initTabs(){
  const panels=[...document.querySelectorAll('.tab-panel')];
  const links=[...document.querySelectorAll('[data-tab-link]')];
  if(!panels.length || !links.length) return;

  const aliases={
    home:'home', news:'news', schedule:'schedule', scores:'scores', rankings:'rankings',
    roster:'roster', stats:'stats', media:'media', history:'history', game:'game'
  };

  function activate(tab, updateHash=true){
    tab=aliases[tab] || 'home';
    panels.forEach(p=>p.classList.toggle('is-active', p.dataset.tab===tab));
    links.forEach(a=>{
      const active=a.dataset.tabLink===tab;
      a.classList.toggle('active',active);
      if(active) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current');
    });
    if(updateHash){
      const target=tab==='home' ? '#home' : (links.find(a=>a.dataset.tabLink===tab)?.getAttribute('href') || '#home');
      history.replaceState(null,'',target);
    }
    window.scrollTo({top:0,behavior:'smooth'});
  }

  links.forEach(a=>{
    if(!a.dataset.tabLink) return;
    a.addEventListener('click',e=>{
      e.preventDefault();
      activate(a.dataset.tabLink);
    });
  });

  document.querySelectorAll('a[href^="#"]').forEach(a=>{
    if(a.dataset.tabLink) return;
    a.addEventListener('click',e=>{
      const id=a.getAttribute('href')?.slice(1);
      const panel=document.getElementById(id);
      if(!panel?.dataset.tab) return;
      e.preventDefault();
      activate(panel.dataset.tab);
    });
  });

  const hash=location.hash.slice(1);
  const hashPanel=document.getElementById(hash);
  activate(hashPanel?.dataset.tab || (hash ? hash : 'home'), false);
})();

function renderStatsDashboard(stats) {
  if (!stats) return;
  const through = document.getElementById("stats-through");
  if (through) through.textContent = stats.through || "Current season";

  const summary = document.getElementById("stats-summary");
  if (summary && Array.isArray(stats.team_summary)) {
    summary.innerHTML = stats.team_summary.map(x => `<div><b>${escapeHtml(x.value)}</b><span>${escapeHtml(x.label)}</span><small>${escapeHtml(x.note || "")}</small></div>`).join("");
  }

  renderStatList("stats-offense", stats.offense);
  renderStatList("stats-defense", stats.defense);
  renderStatList("stats-situational", stats.situational, true);

  const leaders = document.getElementById("stats-leaders");
  if (leaders && stats.leaders) {
    const groups = [
      ["PASSING", stats.leaders.passing || []],
      ["RUSHING", stats.leaders.rushing || []],
      ["RECEIVING", stats.leaders.receiving || []],
      ["DEFENSE", stats.leaders.defense || []]
    ];
    leaders.innerHTML = groups.map(([label,items]) => {
      const top = items[0] || {player:"—",line:"No stats yet",extra:""};
      return `<div class="leader-card"><div class="eyebrow">${label}</div><h4>${escapeHtml(top.player)}</h4><p>${escapeHtml(top.line)}</p><small>${escapeHtml(top.extra || "")}</small>${items.length>1 ? items.slice(1).map(i=>`<div class="leader-more"><b>${escapeHtml(i.player)}</b><span>${escapeHtml(i.line)}</span></div>`).join("") : ""}</div>`;
    }).join("");
  }

  const log = document.getElementById("stats-game-log");
  if (log && Array.isArray(stats.game_log)) {
    log.innerHTML = stats.game_log.map(g => `<div class="game-log-row"><span class="week">${escapeHtml(g.week || "")}</span><span class="opp">${escapeHtml(g.opponent || "")}</span><span class="result ${String(g.result||"").startsWith("W") ? "win" : ""}">${escapeHtml(g.result || "")}</span><span class="yards">YDS ${escapeHtml(g.yards || "—")}</span><span class="to">TO ${escapeHtml(g.turnovers || "—")}</span></div><div class="game-log-note">${escapeHtml(g.notes || "")}</div>`).join("");
  }
}

function renderStatList(id, rows, situational=false) {
  const el = document.getElementById(id);
  if (!el || !Array.isArray(rows)) return;
  el.innerHTML = rows.map(row => {
    const label=row[0] || "", value=row[1] || "", note=row[2] || "";
    return `<div><span>${escapeHtml(label)}${note ? `<small>${escapeHtml(note)}</small>` : ""}</span><b class="stat-value">${escapeHtml(value)}</b></div>`;
  }).join("");
}


// Griz HQ automatic data refresh: GitHub Actions updates data.json, and the
// browser checks the site data periodically so game results/next opponent/etc.
// appear without requiring the visitor to manually reload the page.
setInterval(async () => {
  try {
    await loadGrizData();
    await renderBigSkyAndOpponent();
    await renderFCSScoreboard();
  } catch (e) {
    console.warn("Automatic Griz HQ refresh failed", e);
  }
}, 60 * 1000);
