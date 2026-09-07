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
function isMontanaGrizzlies(team) {
  const s = String(team || "").toLowerCase().trim();
  // Highlight Montana only. Never highlight Montana State/Bobcats.
  if (!s.includes("montana")) return false;
  if (/\bmontana\s+(?:state|st\.?)(?:\b|\.)/i.test(s)) return false;
  if (s.includes("bobcats")) return false;
  return true;
}
function renderPoll(id, teams) {
  const el = document.getElementById(id);
  if (!el || !Array.isArray(teams)) return;
  el.innerHTML = teams.slice(0,20).map(t => `<li class="${isMontanaGrizzlies(t) ? "griz" : ""}">${escapeHtml(t)}</li>`).join("");
}
function renderMiniPolls(coaches, media) {
  const wrap = document.getElementById("rankings-mini");
  if (!wrap || !Array.isArray(coaches) || !Array.isArray(media)) return;
  wrap.innerHTML = [coaches, media].map(poll => `<ol>${poll.slice(0,10).map(t => `<li class="${isMontanaGrizzlies(t) ? "griz" : ""}">${escapeHtml(t)}</li>`).join("")}</ol>`).join("");
}
function escapeHtml(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }

async function renderLatestPressConference(){
  const box=document.getElementById("latest-press");
  if(!box)return;
  try{
    const d=await (await fetch("data.json?ts="+Date.now(),{cache:"no-store"})).json();
    const m=d.latest_press_conference;
    if(!m)return;
    const pressTitle=String(m.title||'').toLowerCase();
    if(pressTitle.includes('montana state') || pressTitle.includes('montana st.') || pressTitle.includes('bobcats') || pressTitle.includes('bozeman')) return;
    const title=document.getElementById("latest-press-title");
    const date=document.getElementById("latest-press-date");
    const link=document.getElementById("latest-press-link");
    const video=document.getElementById("latest-press-video");
    if(title)title.textContent=m.title||"Latest Griz press conference";
    if(date)date.textContent=(m.date?m.date+" • ":"")+"Skyline Sports";
    if(link)link.href=m.url||"https://skylinesportsmt.com/category/press-conference/";
    if(video){
      if(m.youtube_id){
        video.innerHTML='<iframe src="https://www.youtube.com/embed/'+encodeURIComponent(m.youtube_id)+'?rel=0" title="Latest Griz press conference" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>';
      } else {
        video.innerHTML='<div class="press-video-placeholder">Skyline has published the press conference article. The video player will appear automatically when the YouTube video is attached.</div>';
      }
    }
  }catch(e){}
}

loadGrizData();
renderLatestPressConference();

function renderDepthChart(d) {
  const dc = d.depth_chart;
  if (!dc) return;
  const note = document.getElementById("depth-chart-note");
  const updated = document.getElementById("depth-chart-updated");
  const sourceButton = document.getElementById("depth-chart-source");
  if (note) note.innerHTML = `${escapeHtml(dc.note || "Latest published two-deep")} <a href="${dc.source_url || "#"}" target="_blank" rel="noopener">Source ↗</a>`;
  if (updated) updated.textContent = dc.published ? `Published ${dc.published}` : "2026 season";
  if (sourceButton && dc.source_url) sourceButton.href = dc.source_url;
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

    const nextLogo = document.getElementById("next-opponent-logo");
    const nextLogos = {
      "Utah Tech": "https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png",
      "Oregon State": "https://a.espncdn.com/i/teamlogos/ncaa/500/204.png",
      "UC Davis": "https://a.espncdn.com/i/teamlogos/ncaa/500/302.png",
      "Northern Colorado": "https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png",
      "Northern Arizona": "https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png",
      "Idaho": "https://a.espncdn.com/i/teamlogos/ncaa/500/70.png",
      "Eastern Washington": "https://a.espncdn.com/i/teamlogos/ncaa/500/331.png",
      "Portland State": "https://a.espncdn.com/i/teamlogos/ncaa/500/2502.png",
      "Idaho State": "https://a.espncdn.com/i/teamlogos/ncaa/500/304.png",
      "Montana State": "https://a.espncdn.com/i/teamlogos/ncaa/500/147.png"
    };
    if (nextLogo && nextLogos[opponent]) { nextLogo.src = nextLogos[opponent]; nextLogo.alt = `${opponent} logo`; }
    const nextDateEl=document.getElementById("next-game-date"), nextTimeEl=document.getElementById("next-game-time"), nextVenueEl=document.getElementById("next-game-venue");
    if(nextDateEl && d.next_game?.date) nextDateEl.textContent=String(d.next_game.date).toUpperCase();
    if(nextTimeEl && d.next_game?.time) nextTimeEl.textContent=String(d.next_game.time).toUpperCase();
    if(nextVenueEl && d.next_game?.venue) nextVenueEl.textContent=String(d.next_game.venue).split(",")[0].toUpperCase();

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
  function teamKeys(s){
    const raw=String(s||'').toLowerCase().replace(/&/g,' and ').replace(/[^a-z0-9]+/g,' ').trim();
    const tokens=raw?raw.split(/\s+/):[];
    const expand={
      'st':'state','st.':'state','n':'north','n.':'north','s':'south','s.':'south',
      'e':'eastern','e.':'eastern','w':'west','w.':'west',
      'no':'north','n.':'north'
    };
    const expanded=tokens.map(t=>expand[t]||t);
    const keys=new Set([norm(s),norm(tokens.join(' ')),norm(expanded.join(' '))]);
    return [...keys].filter(Boolean);
  }
  // ESPN's names are not consistent across endpoints (e.g. Montana State,
  // Montana St., Montana State Bobcats). Prefer ESPN team IDs, then fall back
  // to normalized names/aliases so a naming change cannot hide a game.
  const teamIds={
    'montana':'149',
    'montanastate':'147',
    'idaho':'70',
    'weberstate':'2692',
    'easternwashington':'331',
    'northernarizona':'2464',
    'northerncolorado':'2458',
    'idahostate':'304',
    'calpoly':'13',
    'southernutah':'253',
    'utahtech':'3101',
    'ucdavis':'302',
    'portlandstate':'2502'
  };
  const teamAliases={
    'montana':['montana','montanagrizzlies'],
    'montanastate':['montanastate','montanast','montanastatebobcats'],
    'idaho':['idaho','idahovandals'],
    'weberstate':['weberstate','weberst','weberstatewildcats'],
    'easternwashington':['easternwashington','ewashington','easternwash','easternwashingtoneagles'],
    'northernarizona':['northernarizona','narizona','northernaz','northernarizonalumberjacks'],
    'northerncolorado':['northerncolorado','ncolorado','northerncoloradobears'],
    'idahostate':['idahostate','idahost','idst','idahostatebengals'],
    'calpoly':['calpoly','calpolytechnic','calpolymustangs'],
    'southernutah':['southernutah','southeasternutah','soutah','soututah','southernutahthunderbirds'],
    'utahtech':['utahtech','utahtechuniversity','utahtechtrailblazers'],
    'ucdavis':['ucdavis','ucdavisaggies'],
    'portlandstate':['portlandstate','portlandst','portlandstatevikings'],
    'westerncarolina':['westerncarolina','westerncarolinacatamounts'],
    'abilenechristian':['abilenechristian','abilenechrstn','abilenechristianwildcats','acu'],
    'stephenfaustin':['stephenfaustin','sfaustin','sfaustinlumberjacks','sfa','sfjacks','sf']
  };
  function canonicalTeamKey(s){
    const keys=teamKeys(s);
    for(const [key,variants] of Object.entries(teamAliases)){
      const v=variants.map(norm);
      if(keys.some(k=>v.includes(k))) return key;
    }
    return null;
  }
  function looseTeamMatch(a,b){
    const ak=teamKeys(a), bk=teamKeys(b);
    if(ak.some(k=>bk.includes(k))) return true;
    const ca=canonicalTeamKey(a), cb=canonicalTeamKey(b);
    if(ca && cb && ca===cb) return true;
    // Handle common ESPN short forms for non-Big-Sky FCS teams.
    const compact=x=>norm(x);
    const special={
      'abilenechrstn':'abilenechristian','acuwildcats':'abilenechristian',
      'sfAustin':'stephenfaustin','sfaustin':'stephenfaustin','sfa':'stephenfaustin',
      'westerncarolinacatamounts':'westerncarolina'
    };
    const aa=ak.map(k=>special[k]||k), bb=bk.map(k=>special[k]||k);
    return aa.some(k=>bb.includes(k));
  }
  function teamMatches(name,team){
    if(!name || !team) return false;
    // If either side is an ESPN team object, IDs are the most reliable match.
    if(typeof name==='object' || typeof team==='object'){
      const a=typeof name==='object'?name:null, b=typeof team==='object'?team:null;
      if(a?.id && b?.id && String(a.id)===String(b.id)) return true;
      const ak=canonicalTeamKey(a?.name||a?.short||a?.abbrev||'');
      const bk=canonicalTeamKey(b?.name||b?.short||b?.abbrev||'');
      return !!ak && ak===bk;
    }
    if(looseTeamMatch(name,team)) return true;
    const a=canonicalTeamKey(name), b=canonicalTeamKey(team);
    return !!a && a===b;
  }
  function teamObjectMatches(canonical,team){
    if(!team) return false;
    const key=canonicalTeamKey(canonical) || norm(canonical);
    if(team.id && teamIds[key] && String(team.id)===String(teamIds[key])) return true;
    return teamMatches(canonical,team.name) || teamMatches(canonical,team.short) || teamMatches(canonical,team.abbrev);
  }
  function findTeamEvent(name,events){
    return events.find(ev=>(ev.teams||[]).some(t=>teamObjectMatches(name,t)))||null;
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
    const me=(ev.teams||[]).find(x=>teamObjectMatches(name,x));
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
      const isGriz=teamMatches('Montana',t.team);
      const cardClass=isGriz?'griz':'';
      const rank=escapeHtml(t.rank);
      const teamLogo=(x)=>{
        const id=x?.team?.id || x?.id;
        const direct=x?.team?.logo || x?.logo;
        return direct || (id ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id)}.png` : '');
      };
      const teamRow=(x)=>{
        const name=x?.short||x?.name||'Team';
        const logo=teamLogo(x);
        return `<div class="fcs-top-team-row">${logo?`<img src="${escapeHtml(logo)}" alt="" loading="lazy">`:''}<span>${escapeHtml(name)}</span><strong>${escapeHtml(x?.score??'—')}</strong></div>`;
      };
      if(ev){
        const away=(ev.teams||[]).find(x=>x.homeAway==='away') || (ev.teams||[])[0];
        const home=(ev.teams||[]).find(x=>x.homeAway==='home') || (ev.teams||[])[1];
        const statusLabel=ev.completed ? 'FINAL' : (ev.state==='in' ? statusText(ev) : (ev.date?new Date(ev.date).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'TBA'));
        return `<div class="fcs-rank-card ${cardClass}"><span class="fcs-rank">${rank}</span><div class="fcs-top-matchup">${teamRow(away)}${teamRow(home)}<small>${escapeHtml(statusLabel)}</small></div></div>`;
      }
      const fallbackLogo=t.logo||t.logo_url||'';
      const fallbackRow=`<div class="fcs-top-team-row">${fallbackLogo?`<img src="${escapeHtml(fallbackLogo)}" alt="" loading="lazy">`:''}<span>${escapeHtml(t.team)}</span><strong>—</strong></div>`;
      return `<div class="fcs-rank-card ${cardClass}"><span class="fcs-rank">${rank}</span><div class="fcs-top-matchup">${fallbackRow}<small>${escapeHtml(t.record||'')} • NO GAME THIS WEEK</small></div></div>`;
    }).join('');

    if(bigSkyEl){
      bigSkyEl.innerHTML=bigSkyTeams.map(team=>{
        const ev=findTeamEvent(team,events);
        if(!ev)return `<div class="fcs-game scheduled bigsky-row bye"><div class="fcs-time">BYE</div><div class="fcs-matchup"><b>${escapeHtml(team)}</b><small>NO GAME THIS WEEK</small></div><div class="fcs-score">BYE</div><div class="fcs-tv"></div></div>`;
        const d=gameLabel(ev);
        const label=(team==='Weber State'&&[d.away,d.home].includes('Southern Utah'))||(team==='Southern Utah'&&[d.away,d.home].includes('Weber State'))?'NON-CONFERENCE':'BIG SKY';
        const tv=(ev.broadcasts||[]).slice(0,2).join(', ');
        const state=ev.state==='in'?'live':(ev.completed?'final':'scheduled');
        const away=(ev.teams||[]).find(x=>x.homeAway==='away') || (ev.teams||[])[0];
        const home=(ev.teams||[]).find(x=>x.homeAway==='home') || (ev.teams||[])[1];
        const teamLogo=(x)=>{
          const id=x?.team?.id || x?.id;
          const direct=x?.team?.logo || x?.logo;
          return direct || (id ? `https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id)}.png` : '');
        };
        const teamRow=(x)=>{
          const name=x?.short||x?.name||'Team';
          const logo=teamLogo(x);
          return `<div class="score-team-row">${logo?`<img src="${escapeHtml(logo)}" alt="" loading="lazy">`:''}<span>${escapeHtml(name)}</span><strong>${escapeHtml(x?.score??'—')}</strong></div>`;
        };
        const statusLabel=ev.completed ? 'FINAL' : (ev.state==='in' ? statusText(ev) : d.time);
        return `<div class="fcs-game ${state} bigsky-row"><div class="fcs-time">${escapeHtml(label)}</div><div class="fcs-matchup">${teamRow(away)}${teamRow(home)}<small class="score-game-status">${escapeHtml(statusLabel)}${tv?` • ${escapeHtml(tv)}`:''}</small></div><div class="fcs-score score-status">${escapeHtml(statusLabel)}</div><div class="fcs-tv">${escapeHtml(tv)}</div></div>`;
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

  const compare = document.getElementById("stats-compare");
  if (compare && Array.isArray(stats.compare)) {
    compare.innerHTML = `<div class="stats-compare-head"><span>TEAM STAT</span><b>MONTANA</b><b>OPPONENTS</b><strong>DIFF</strong></div>` +
      stats.compare.map(r => `<div class="stats-compare-row"><span>${escapeHtml(r.label)}</span><b>${escapeHtml(r.montana)}</b><b>${escapeHtml(r.opponents)}</b><strong class="${String(r.diff||'').startsWith('+') ? 'positive' : String(r.diff||'').startsWith('-') ? 'negative' : ''}">${escapeHtml(r.diff || '—')}</strong></div>`).join("");
  }

  const leaders = document.getElementById("stats-leaders");
  if (leaders && stats.leaders) {
    const groups = [
      ["PASSING", stats.leaders.passing || []],
      ["RUSHING", stats.leaders.rushing || []],
      ["RECEIVING", stats.leaders.receiving || []],
      ["TACKLES", stats.leaders.tackles || stats.leaders.defense || []],
      ["TFL / SACKS", stats.leaders.pressure || []],
      ["SPECIAL TEAMS", stats.leaders.special || []]
    ];
    leaders.innerHTML = groups.map(([label,items]) => {
      const top = items[0] || {player:"—",line:"No stats yet",extra:""};
      return `<div class="leader-card"><div class="eyebrow">${label}</div><h4>${escapeHtml(top.player)}</h4><p>${escapeHtml(top.line)}</p><small>${escapeHtml(top.extra || "")}</small>${items.length>1 ? items.slice(1,5).map(i=>`<div class="leader-more"><b>${escapeHtml(i.player)}</b><span>${escapeHtml(i.line)}</span></div>`).join("") : ""}</div>`;
    }).join("");
  }

  const trends = document.getElementById("stats-trends");
  if (trends && Array.isArray(stats.game_log)) {
    const maxY = Math.max(1, ...stats.game_log.map(g => Number(g.montana_yards || 0)), ...stats.game_log.map(g => Number(g.opponent_yards || 0)));
    trends.innerHTML = stats.game_log.map(g => {
      const my = Number(g.montana_yards || 0), oy = Number(g.opponent_yards || 0);
      return `<div class="trend-row"><div class="trend-meta"><b>${escapeHtml(g.week || "")}</b><span>${escapeHtml(g.opponent || "")}</span><strong>${escapeHtml(g.result || "")}</strong></div><div class="trend-bars"><div><span>MT</span><i style="width:${Math.round(my/maxY*100)}%"></i><b>${my}</b></div><div><span>OPP</span><i style="width:${Math.round(oy/maxY*100)}%"></i><b>${oy}</b></div></div></div>`;
    }).join("");
  }

  const log = document.getElementById("stats-game-log");
  if (log && Array.isArray(stats.game_log)) {
    log.innerHTML = stats.game_log.map(g => `<div class="game-log-row"><span class="week">${escapeHtml(g.week || "")}</span><span class="opp">${escapeHtml(g.opponent || "")}</span><span class="result ${String(g.result||"").startsWith("W") ? "win" : ""}">${escapeHtml(g.result || "")}</span><span class="yards">${escapeHtml(g.montana_yards || "—")}–${escapeHtml(g.opponent_yards || "—")}</span><span class="to">${escapeHtml(g.turnovers || "—")}</span></div><div class="game-log-note">${escapeHtml(g.notes || "")}</div>`).join("");
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
