
const GRIZ_GAME_VENUES = {
  "Southern Utah": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Drake": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Utah Tech": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Oregon State": {lat:44.5595, lon:-123.2800, venue:"Reser Stadium"},
  "UC Davis": {lat:38.5418, lon:-121.7505, venue:"UC Davis Health Stadium"},
  "Northern Colorado": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Northern Arizona": {lat:35.1894, lon:-111.6513, venue:"J. Lawrence Walkup Skydome"},
  "Idaho": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Eastern Washington": {lat:47.4917, lon:-117.5830, venue:"Roos Field"},
  "Portland State": {lat:45.5481, lon:-122.6890, venue:"Hillsboro Stadium"},
  "Idaho State": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Montana State": {lat:45.6676, lon:-111.0490, venue:"Bobcat Stadium"}
};

const GRIZ_SCHEDULE_LOGOS = {
  "Montana": "https://a.espncdn.com/i/teamlogos/ncaa/500/149.png",
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
  "Montana State": "https://a.espncdn.com/i/teamlogos/ncaa/500/147.png",
  "Lamar": "https://a.espncdn.com/i/teamlogos/ncaa/500/2320.png",
  "South Dakota": "https://a.espncdn.com/i/teamlogos/ncaa/500/233.png",
  "Wyoming": "https://a.espncdn.com/i/teamlogos/ncaa/500/2751.png",
  "Incarnate Word": "https://a.espncdn.com/i/teamlogos/ncaa/500/2916.png",
  "Colorado State": "https://a.espncdn.com/i/teamlogos/ncaa/500/36.png",
  "San Jose State": "https://a.espncdn.com/i/teamlogos/ncaa/500/23.png",
  "North Dakota": "https://a.espncdn.com/i/teamlogos/ncaa/500/155.png",
  "Nevada": "https://a.espncdn.com/i/teamlogos/ncaa/500/2440.png"
};

function scheduleLogo(name) {
  const key = String(name || '').trim();
  return GRIZ_SCHEDULE_LOGOS[key] || '';
}

function scheduleDateISO(label) {
  const m = String(label || '').trim().toUpperCase().match(/^([A-Z]{3})\s+(\d{1,2})/);
  if (!m) return null;
  const months = {JAN:'01',FEB:'02',MAR:'03',APR:'04',MAY:'05',JUN:'06',JUL:'07',AUG:'08',SEP:'09',OCT:'10',NOV:'11',DEC:'12'};
  return months[m[1]] ? `2026-${months[m[1]]}-${String(m[2]).padStart(2,'0')}` : null;
}

function formatOdds(odds) {
  if (!odds) return {provider:'LINE NOT POSTED', spread:'—', total:'—', moneyline:'—'};
  const provider = odds.provider?.name || odds.provider?.displayName || 'SPORTSBOOK';
  const details = odds.details || odds.spread || '—';
  const total = odds.overUnder != null ? odds.overUnder : '—';
  let moneyline = '—';
  if (Array.isArray(odds.moneyline)) {
    moneyline = odds.moneyline.map(x => x.value ?? x.displayValue).filter(Boolean).join(' / ') || '—';
  } else if (odds.moneyline) {
    moneyline = odds.moneyline.displayValue || odds.moneyline.value || '—';
  }
  return {provider, spread:details || '—', total, moneyline};
}

async function fetchGameOdds(game) {
  const iso = scheduleDateISO(game.date);
  if (!iso || game.result) return null;
  try {
    const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${iso.replaceAll('-','')}&limit=500`, {cache:'no-store'});
    if (!r.ok) return null;
    const d = await r.json();
    const event = (d.events || []).find(e => {
      const name = String(e.name || '').toLowerCase();
      return name.includes('montana') && name.includes(String(game.opponent || '').toLowerCase());
    });
    const odds = event?.competitions?.[0]?.odds;
    if (!odds) return null;
    const first = Array.isArray(odds) ? odds[0] : odds;
    return formatOdds(first);
  } catch (e) { return null; }
}

function weatherLabel(code) {
  const c = Number(code);
  if ([0].includes(c)) return 'Clear';
  if ([1,2].includes(c)) return 'Mostly clear';
  if ([3].includes(c)) return 'Cloudy';
  if ([45,48].includes(c)) return 'Fog';
  if ([51,53,55,56,57].includes(c)) return 'Drizzle';
  if ([61,63,65,66,67].includes(c)) return 'Rain';
  if ([71,73,75,77].includes(c)) return 'Snow';
  if ([80,81,82].includes(c)) return 'Showers';
  if ([95,96,99].includes(c)) return 'Thunderstorms';
  return 'Forecast available';
}

async function fetchGameWeather(game) {
  const iso = scheduleDateISO(game.date), loc = GRIZ_GAME_VENUES[game.opponent];
  if (!iso || !loc || game.result) return null;
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${loc.lat}&longitude=${loc.lon}&daily=weather_code,temperature_2m_max,precipitation_probability_max,wind_speed_10m_max&timezone=auto&start_date=${iso}&end_date=${iso}`;
    const r = await fetch(url, {cache:'no-store'});
    if (!r.ok) return null;
    const d = await r.json();
    if (!d.daily?.time?.length) return null;
    return {
      temp: Math.round(Number(d.daily.temperature_2m_max?.[0])),
      rain: Number(d.daily.precipitation_probability_max?.[0] ?? 0),
      wind: Math.round(Number(d.daily.wind_speed_10m_max?.[0] ?? 0)),
      condition: weatherLabel(d.daily.weather_code?.[0])
    };
  } catch (e) { return null; }
}

async function enrichScheduleCards(schedule, games) {
  const upcoming = games.filter(g => !g.result);
  const enriched = await Promise.all(upcoming.map(async g => ({
    key: `${g.date}|${g.opponent}`,
    odds: await fetchGameOdds(g),
    weather: await fetchGameWeather(g)
  })));
  const map = new Map(enriched.map(x => [x.key, x]));
  schedule.querySelectorAll('.schedule-row[data-game-key]').forEach(row => {
    const item = map.get(row.dataset.gameKey);
    if (!item) return;
    const odds = item.odds;
    const weather = item.weather;
    const oddsEl = row.querySelector('.schedule-odds');
    const weatherEl = row.querySelector('.schedule-weather');
    if (oddsEl) {
      oddsEl.innerHTML = odds
        ? `<b>${escapeHtml(odds.spread)}</b><span>O/U ${escapeHtml(String(odds.total))}</span><span>ML ${escapeHtml(String(odds.moneyline))}</span><small>${escapeHtml(odds.provider)}</small>`
        : `<b>NOT POSTED</b><span>Sportsbook line unavailable</span>`;
    }
    if (weatherEl) {
      weatherEl.innerHTML = weather
        ? `<b>${escapeHtml(String(weather.temp))}°</b><span>${escapeHtml(weather.condition)}</span><span>${escapeHtml(String(weather.rain))}% rain · ${escapeHtml(String(weather.wind))} mph</span><small>Open-Meteo forecast</small>`
        : `<b>FORECAST TBD</b><span>Closer to kickoff</span>`;
    }
  });
}

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
      const firstUpcoming = d.schedule.findIndex(x => !x.result);
      schedule.innerHTML = `<div class="schedule-row head"><span>DATE</span><span>OPPONENT</span><span>RESULT / TIME</span></div>` +
        d.schedule.map((g, i) => {
          const isNext = !g.result && i === firstUpcoming;
          const key = `${g.date || ""}|${g.opponent || ""}`;
          const venue = g.venue || GRIZ_GAME_VENUES[g.opponent]?.venue || (g.location === "Away" ? "Road game" : "Washington-Grizzly Stadium");
          const tv = g.tv || g.network || "";
          const status = g.result || g.time || "";
          return `<div class="schedule-row game-card-row ${isNext ? "next" : ""} ${g.result ? "played" : "upcoming"}" data-game-key="${escapeHtml(key)}">
            <div class="schedule-main-date"><span>${escapeHtml(g.date || "")}</span><small>${g.location === "Away" ? "AWAY" : "HOME"}</small></div>
            <div class="schedule-main-match"><div class="schedule-team-line"><img src="${scheduleLogo(g.opponent)}" alt="${escapeHtml(g.opponent || "Opponent")} logo" loading="lazy" onerror="this.style.display='none'"><b>${g.location === "Away" ? "@ " : ""}${escapeHtml(g.opponent || "")}</b></div><span>${escapeHtml(venue)}</span>${tv ? `<small>${escapeHtml(tv)}</small>` : ""}</div>
            <div class="schedule-main-status"><strong>${escapeHtml(status)}</strong>${isNext ? `<em>NEXT GAME</em>` : (g.result ? `<em>FINAL</em>` : `<em>UPCOMING</em>`)}</div>
          </div>`;
        }).join("");
      // Main Griz schedule intentionally stays clean: no sportsbook/weather columns.
      // The separate Around the League / Big Sky board handles market + weather data.
    }

    renderStatsDashboard(d.stats);

    // Use a verified poll snapshot immediately so the page never falls back
    // to the stale preseason data.json rankings. Each entry carries the
    // previous-week rank, so movement is calculated/displayed correctly.
    applyRankingSnapshotFallback();
    const rankDate = document.getElementById("rankings-date");

    try {
      const livePoll = await fetchLiveFCSCoachesPoll();
      renderPoll("coaches-poll", livePoll.teams);
      renderMiniPolls(livePoll.teams, d.media_poll);
      if (rankDate) rankDate.textContent = "LIVE • " + (livePoll.date ? new Date(livePoll.date).toLocaleDateString([], {month:"short", day:"numeric", year:"numeric"}) : "Current poll");
      const liveBadge = document.getElementById("rankings-live-status");
      if (liveBadge) liveBadge.textContent = "LIVE FCS COACHES POLL";
    } catch (rankErr) {
      console.warn("Live FCS rankings unavailable; using verified ranking snapshot", rankErr);
      applyRankingSnapshotFallback();
    }
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
async function fetchLiveFCSCoachesPoll() {
  // ESPN publishes the FCS Coaches Poll. Keep the live poll independent of
  // Griz HQ's local data.json so the rankings can update when the poll changes.
  const url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings?seasontype=2&type=0&level=3&ts=" + Date.now();
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("FCS rankings request failed: " + res.status);
  const data = await res.json();
  const polls = Array.isArray(data.rankings) ? data.rankings : [];
  const poll = polls.find(p => /FCS.*Coach|Coach.*FCS/i.test(String(p.name || p.headline || ""))) || polls[2];
  if (!poll || !Array.isArray(poll.ranks) || !poll.ranks.length) throw new Error("No FCS Coaches Poll returned");
  const teams = poll.ranks.slice(0, 25).map(r => {
    const t = r.team || {};
    const name = t.school || t.location || t.displayName || t.shortDisplayName || t.name || t.abbreviation || "Team";
    const rank = Number(r.current ?? r.rank);
    const previous = Number(r.previous ?? r.previousRank);
    const hasPrevious = Number.isFinite(previous) && previous > 0;
    const delta = hasPrevious && Number.isFinite(rank) ? previous - rank : null;
    const record = t.record || t.records?.[0]?.summary || "";
    return { rank, previous: hasPrevious ? previous : null, delta, name, record };
  });
  // ESPN can temporarily return the preseason FCS poll after a new weekly poll
  // has been released elsewhere. A real weekly poll should contain previous
  // ranks for most teams. Reject an all-NEW response so we use the verified
  // weekly snapshot instead of displaying the stale preseason poll.
  const withPrevious = teams.filter(t => t.previous != null).length;
  if (withPrevious < 10) throw new Error("ESPN returned a stale/preseason FCS poll");
  const date = poll.lastUpdated || poll.date || data.lastUpdated || "";
  return { teams, date, name: poll.name || poll.headline || "FCS Coaches Poll" };
}


const RANKING_SNAPSHOTS = {
  coaches: {
    date: "Aug. 31, 2026",
    teams: [
      [1,"Montana State",1],[2,"South Dakota State",3],[3,"Montana",2],[4,"Illinois State",4],[5,"Tarleton State",5],[6,"UC Davis",6],[7,"Youngstown State",9],[8,"Rhode Island",8],[9,"North Dakota",10],[10,"Lehigh",11],[11,"Stephen F. Austin",13],[12,"South Dakota",12],[13,"Tennessee Tech",15],[14,"Austin Peay",18],[15,"Mercer",17],[16,"Lamar",21],[17,"Villanova",7],[18,"Yale",19],[19,"William & Mary",null],[20,"Northern Arizona",24],[21,"Abilene Christian",14],[22,"South Carolina State",25],[23,"Richmond",null],[24,"Central Arkansas",null],[25,"Southern Illinois",16]
    ].map(([rank,name,previous]) => ({rank,name,previous,delta:previous==null?null:previous-rank,record:""}))
  },
  media: {
    date: "Sept. 7, 2026",
    teams: [
      [1,"Montana State",1],[2,"South Dakota State",2],[3,"Montana",3],[4,"Tarleton State",5],[5,"Illinois State",4],[6,"North Dakota",8],[7,"UC Davis",7],[8,"Rhode Island",6],[9,"Lehigh",10],[10,"Youngstown State",9],[11,"South Dakota",11],[12,"Tennessee Tech",12],[13,"Stephen F. Austin",13],[14,"Lamar",14],[15,"Austin Peay",15],[16,"William & Mary",17],[17,"Idaho State",23],[18,"Mercer",19],[19,"Yale",16],[20,"West Florida",25],[21,"Villanova",18],[22,"South Carolina State",21],[23,"Abilene Christian",20],[24,"Northern Arizona",22],[25,"Harvard",null]
    ].map(([rank,name,previous]) => ({rank,name,previous,delta:previous==null?null:previous-rank,record:""}))
  }
};
function applyRankingSnapshotFallback() {
  renderPoll("coaches-poll", RANKING_SNAPSHOTS.coaches.teams);
  renderPoll("media-poll", RANKING_SNAPSHOTS.media.teams);
  window.__grizMediaPoll = RANKING_SNAPSHOTS.media.teams;
  renderMiniPolls(RANKING_SNAPSHOTS.coaches.teams, RANKING_SNAPSHOTS.media.teams);
  const rankDate = document.getElementById("rankings-date");
  if (rankDate) rankDate.textContent = `Coaches • ${RANKING_SNAPSHOTS.coaches.date} | Stats Perform • ${RANKING_SNAPSHOTS.media.date}`;
}

function rankingMovementMarkup(t) {
  if (!t || !Number.isFinite(t.rank)) return "";
  if (t.previous == null) return '<span class="rank-movement rank-new">NEW</span>';
  if (t.delta > 0) return `<span class="rank-movement rank-up">▲ ${escapeHtml(t.delta)}</span>`;
  if (t.delta < 0) return `<span class="rank-movement rank-down">▼ ${escapeHtml(Math.abs(t.delta))}</span>`;
  return '<span class="rank-movement rank-same">—</span>';
}

function normalizeRankingEntry(t, fallbackRank) {
  if (t && typeof t === "object") {
    const copy = { ...t };
    if (!Number.isFinite(Number(copy.rank)) && Number.isFinite(Number(fallbackRank))) copy.rank = Number(fallbackRank);
    return copy;
  }
  const raw = String(t ?? "").trim();
  const m = raw.match(/^\s*(?:(\d+)\.\s*)?(.*?)(?:\s*\(([^)]*)\))?(?:\s*(?:↑|▲)(\d+)|\s*(?:↓|▼)(\d+))?\s*$/);
  if (!m) return { rank: Number(fallbackRank) || null, previous: null, delta: null, name: raw, record: "" };
  const rank = Number(m[1] || fallbackRank);
  const delta = m[4] ? Number(m[4]) : (m[5] ? -Number(m[5]) : null);
  return { rank: Number.isFinite(rank) ? rank : null, previous: delta == null ? null : rank + delta, delta, name: m[2].trim(), record: m[3] || "" };
}

function renderPoll(id, teams) {
  const el = document.getElementById(id);
  if (!el || !Array.isArray(teams)) return;
  el.innerHTML = teams.slice(0, 25).map((t0, i) => {
    const t = normalizeRankingEntry(t0, i + 1);
    const rank = Number.isFinite(t.rank) ? t.rank + "." : (i + 1) + ".";
    const cleanName = String(t.name || "Team").replace(/\s*\([^)]*\)\s*$/, "").trim();
    const record = t.record ? ` <small class="rank-record">(${escapeHtml(t.record)})</small>` : "";
    return `<li><span class="rank-number">${escapeHtml(rank)}</span><span class="rank-team-name">${escapeHtml(cleanName)}</span>${record}${rankingMovementMarkup(t)}</li>`;
  }).join("");
}

function renderMiniPolls(coaches, media) {
  const wrap = document.getElementById("rankings-mini");
  if (!wrap || !Array.isArray(coaches) || !Array.isArray(media)) return;
  wrap.innerHTML = [coaches, media].map(poll => `<ol>${poll.slice(0,10).map(t0 => {
    const t = normalizeRankingEntry(t0);
    const rank = Number.isFinite(t.rank) ? t.rank + "." : "";
    return `<li><span class="rank-number">${escapeHtml(rank)}</span><span class="rank-team-name">${escapeHtml(t.name)}</span>${rankingMovementMarkup(t)}</li>`;
  }).join("")}</ol>`).join("");
}
function escapeHtml(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c])); }
function installRankingMovementStyles() {
  if (document.getElementById("griz-ranking-movement-styles")) return;
  const style = document.createElement("style");
  style.id = "griz-ranking-movement-styles";
  style.textContent = `
    #coaches-poll li, #media-poll li { display:flex; align-items:center; gap:.45rem; }
    #coaches-poll .rank-number, #media-poll .rank-number { min-width:2rem; font-weight:800; }
    .rank-team-name { flex:1; }
    .rank-record { opacity:.68; font-size:.78em; }
    .rank-movement { margin-left:auto; padding:.18rem .42rem; border-radius:999px; font-size:.7rem; font-weight:900; letter-spacing:.04em; white-space:nowrap; }
    .rank-up { background:#e6f4ea; color:#187a3d; }
    .rank-down { background:#fbe9e7; color:#a33a2b; }
    .rank-new { background:#eee; color:#333; }
    .rank-same { color:#888; }
    @media (max-width:640px) { .rank-record { display:none; } }
  `;
  document.head.appendChild(style);
}



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

installRankingMovementStyles();
loadGrizData();
renderLatestPressConference();

// Re-check the national FCS Coaches Poll every 30 minutes while the page is open.
setInterval(async () => {
  try {
    const livePoll = await fetchLiveFCSCoachesPoll();
    renderPoll("coaches-poll", livePoll.teams);
    const currentMedia = Array.isArray(window.__grizMediaPoll) ? window.__grizMediaPoll : null;
    if (currentMedia) renderMiniPolls(livePoll.teams, currentMedia);
    const rankDate = document.getElementById("rankings-date");
    if (rankDate) rankDate.textContent = "LIVE • " + (livePoll.date ? new Date(livePoll.date).toLocaleDateString([], {month:"short", day:"numeric", year:"numeric"}) : "Current poll");
  } catch (e) { console.warn("Scheduled rankings refresh failed; retaining verified snapshot", e); applyRankingSnapshotFallback(); }
}, 30 * 60 * 1000);

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

const BIG_SKY_VENUES = {
  "Montana": {lat:46.8721, lon:-113.9940, venue:"Washington-Grizzly Stadium"},
  "Montana State": {lat:45.6676, lon:-111.0490, venue:"Bobcat Stadium"},
  "Idaho": {lat:46.7280, lon:-117.1543, venue:"Kibbie Dome"},
  "Idaho State": {lat:43.6021, lon:-112.0734, venue:"Holt Arena"},
  "Eastern Washington": {lat:47.4917, lon:-117.5830, venue:"Roos Field"},
  "Portland State": {lat:45.5481, lon:-122.6890, venue:"Hillsboro Stadium"},
  "Northern Arizona": {lat:35.1894, lon:-111.6513, venue:"J. Lawrence Walkup Skydome"},
  "Northern Colorado": {lat:40.4064, lon:-104.6974, venue:"Nottingham Field"},
  "Weber State": {lat:41.1919, lon:-111.9459, venue:"Stewart Stadium"},
  "UC Davis": {lat:38.5418, lon:-121.7505, venue:"UC Davis Health Stadium"},
  "Cal Poly": {lat:35.3000, lon:-120.6625, venue:"Alex G. Spanos Stadium"},
  "Sacramento State": {lat:38.5600, lon:-121.4241, venue:"Hornet Stadium"},
  "Utah Tech": {lat:37.1059, lon:-113.5667, venue:"Greater Zion Stadium"},
  // Non-Big-Sky opponents that appear on league schedules.  These are
  // needed so away games can still use the actual home-stadium location
  // for weather instead of falling through to "Forecast unavailable".
  "Colorado": {lat:40.0095, lon:-105.2669, venue:"Folsom Field"},
  "South Dakota": {lat:42.7860, lon:-96.9250, venue:"DakotaDome"},
  "Wyoming": {lat:41.1399, lon:-105.2755, venue:"War Memorial Stadium"},
  "Northwestern State": {lat:31.7556, lon:-93.0978, venue:"Turpin Stadium"},
  "Northeastern State": {lat:36.1551, lon:-94.9678, venue:"Gable Field"},
  "VMI": {lat:37.7879, lon:-79.4428, venue:"Alumni Memorial Field at Foster Stadium"},
  "Drake": {lat:41.6014, lon:-93.6580, venue:"Drake Stadium"},
  "Oregon State": {lat:44.5590, lon:-123.2800, venue:"Reser Stadium"},
  "South Dakota State": {lat:44.3222, lon:-96.7837, venue:"Dana J. Dykhouse Stadium"}
};
const BIG_SKY_WEATHER_CACHE = new Map();
const BIG_SKY_ODDS_CACHE = new Map();
function bigSkyDateISO(label){
  const m = {Aug:8, Sep:9, Oct:10, Nov:11};
  const [mon,day] = String(label||'').trim().split(/\s+/);
  if(!m[mon] || !day) return '';
  return `2026-${String(m[mon]).padStart(2,'0')}-${String(Number(day)).padStart(2,'0')}`;
}
function bigSkyTeamKey(name){
  return String(name||'').toLowerCase().replace(/&/g,'and').replace(/[^a-z0-9]/g,'');
}
function bigSkyVenueFor(game){
  const home = game.location === 'Away' ? game.opponent : game.team;
  return BIG_SKY_VENUES[home] || Object.entries(BIG_SKY_VENUES).find(([k])=>bigSkyTeamKey(k)===bigSkyTeamKey(home))?.[1] || null;
}
function bigSkyFormatOdds(odds){
  if(!odds) return {main:'LINE NOT POSTED', sub:'ESPN • NO CURRENT LINE'};
  const provider = odds.provider?.name || odds.provider?.displayName || odds.providerName || 'ESPN SPORTSBOOK DATA';
  const spread = odds.details || odds.spread || '';
  const totalValue = odds.overUnder ?? odds.total;
  const total = totalValue != null ? `O/U ${totalValue}` : '';

  // ESPN commonly supplies moneylines inside homeTeamOdds / awayTeamOdds.
  // Keep both sides when ESPN provides them so the table is actually useful for betting.
  const ml = [];
  const awayML = odds.awayTeamOdds?.moneyLine ?? odds.awayTeamOdds?.moneyline;
  const homeML = odds.homeTeamOdds?.moneyLine ?? odds.homeTeamOdds?.moneyline;
  if(awayML != null) ml.push(`AWAY ML ${awayML}`);
  if(homeML != null) ml.push(`HOME ML ${homeML}`);
  if(!ml.length && odds.moneyline != null) {
    if(typeof odds.moneyline === 'object') {
      const v = odds.moneyline.displayValue ?? odds.moneyline.value;
      if(v != null) ml.push(`ML ${v}`);
    } else ml.push(`ML ${odds.moneyline}`);
  }

  const parts = [spread,total,...ml].filter(Boolean);
  return {
    main: parts.length ? parts.join(' • ') : 'LINE POSTED',
    sub: `ESPN${provider && provider !== 'ESPN' ? ` • ${provider}` : ''}`
  };
}

function bigSkyNormTeam(name){
  const n=bigSkyTeamKey(name);
  const aliases={
    montanastate:'montanastate',montanast:'montanastate',
    northernarizona:'northernarizona',northernaz:'northernarizona',
    northerncolorado:'northerncolorado',northernco:'northerncolorado',
    idahostate:'idahostate',idahost:'idahostate',
    easternwashington:'easternwashington',easternwa:'easternwashington',
    portlandstate:'portlandstate',portlandst:'portlandstate',
    sacramentostate:'sacramentostate',sacstate:'sacramentostate',
    calpoly:'calpoly',ucdavis:'ucdavis',daviss:'ucdavis',
    webersate:'weberstate',weberstate:'weberstate',
    utahtech:'utahtech',montana:'montana',idaho:'idaho'
  };
  return aliases[n] || n;
}

function bigSkyEventMatches(event, game){
  const comps=event?.competitions?.[0];
  const teams=(comps?.competitors||[]).map(c=>c.team||{});
  const wanted=[bigSkyNormTeam(game.team),bigSkyNormTeam(game.opponent)];
  const have=teams.map(t=>bigSkyNormTeam(t.displayName||t.shortDisplayName||t.name||t.abbreviation||''));
  if(wanted.every(w=>have.some(h=>h===w))) return true;
  const n=bigSkyTeamKey(event?.name||'');
  return wanted.every(w=>n.includes(w));
}

const CIRCA_FCS_URL='https://data.vsin.com/betting-splits/?display=card&league=fcs&source=CIRCA&sport=CFB';
const WAGERTALK_CFB_URL='https://www.wagertalk.com/odds?cb=';
const BIG_SKY_CIRCA_CACHE = new Map();

function circaNorm(s){
  return bigSkyTeamKey(String(s||'').replace(/\b(state|st)\b/gi,'state'));
}
function circaTeamAliases(name){
  const n=circaNorm(name);
  const map={
    montana:['montana','montanagrizzlies'],
    montanastate:['montanastate','montanastbobcats','montanastatebobcats'],
    easternwashington:['easternwashington','easternwashingtoneagles','easternwa'],
    idaho:['idaho','idahovandals'],
    idahostate:['idahostate','idahobengals'],
    northernarizona:['northernarizona','northernaz','northernarizonalumberjacks'],
    northerncolorado:['northerncolorado','northernco','northerncoloradobears'],
    portlandstate:['portlandstate','portlandst','portlandstatevikings'],
    sacramentostate:['sacramentostate','sacstate','sacramentosthornets'],
    ucdavis:['ucdavis','ucdavisdavis','ucd'],
    calpoly:['calpoly','calpolymustangs'],
    weberstate:['weberstate','weberst','weberstatewildcats'],
    utahtech:['utahtech','utahtechtrailblazers'],
    idaho:['idaho','idahovandals'],
    calpoly:['calpoly','calpoly mustangs']
  };
  for(const [k,vals] of Object.entries(map)){ if(vals.includes(n)) return vals; }
  return [n];
}
function circaHasTeam(text,name){ return circaTeamAliases(name).some(a=>text.includes(a)); }
function parseCircaSection(lines,start){
  const out={spread:'',total:'',moneyline:''};
  const slice=lines.slice(start,start+45);
  const spreadAt=slice.findIndex(x=>/Spread Handle Bets/i.test(x));
  const totalAt=slice.findIndex(x=>/Total Handle Bets/i.test(x));
  const mlAt=slice.findIndex(x=>/Money Handle Bets/i.test(x));
  if(spreadAt>=0){ const vals=slice.slice(spreadAt+1,totalAt>spreadAt?totalAt:spreadAt+18).filter(x=>/[+-]\d/.test(x)); out.spread=vals.slice(0,2).join(' / '); }
  if(totalAt>=0){ const vals=slice.slice(totalAt+1,mlAt>totalAt?mlAt:totalAt+12).filter(x=>/^(Over|Under)\b/i.test(x)); out.total=vals.slice(0,2).join(' / '); }
  if(mlAt>=0){ const vals=slice.slice(mlAt+1,Math.min(slice.length,mlAt+12)).filter(x=>/[+-]\d/.test(x)); out.moneyline=vals.slice(0,2).join(' / '); }
  return out;
}
async function fetchCircaOdds(game){
  const key='fcs';
  if(!BIG_SKY_CIRCA_CACHE.has(key)){
    BIG_SKY_CIRCA_CACHE.set(key,(async()=>{
      try{ const r=await fetch(CIRCA_FCS_URL,{cache:'no-store'}); if(!r.ok)return ''; return await r.text(); }catch(e){ return ''; }
    })());
  }
  const html=await BIG_SKY_CIRCA_CACHE.get(key); if(!html)return null;
  const doc=new DOMParser().parseFromString(html,'text/html');
  const text=(doc.body?.innerText||'').replace(/\r/g,'');
  const lines=text.split('\n').map(x=>x.trim()).filter(Boolean);
  const aAliases=circaTeamAliases(game.team), oAliases=circaTeamAliases(game.opponent);
  for(let i=0;i<lines.length;i++){
    const line=circaNorm(lines[i]); if(!line.includes('vs'))continue;
    if(!aAliases.some(a=>line.includes(a))||!oAliases.some(a=>line.includes(a)))continue;
    const parsed=parseCircaSection(lines,i+1);
    if(parsed.spread||parsed.total||parsed.moneyline)return {provider:'CIRCA SPORTS',...parsed};
  }
  return null;
}

function textOddsToken(v){
  const t=String(v||'').replace(/\s+/g,' ').trim();
  if(!t || t==='-' || t==='—') return '';
  return t;
}
function parseBookLine(cellText){
  const parts=String(cellText||'').split(/\n|<br\s*\/?>/i).map(x=>x.trim()).filter(Boolean).filter(x=>x!=='-');
  return parts.slice(0,4);
}
function wagerTeamMatch(text,game){
  const n=circaNorm(text);
  return circaTeamAliases(game.team).some(a=>n.includes(a)) && circaTeamAliases(game.opponent).some(a=>n.includes(a));
}
function extractWagerTalkBookmakers(html,game){
  if(!html)return null;
  const doc=new DOMParser().parseFromString(html,'text/html');
  const tables=[...doc.querySelectorAll('table')];
  for(const table of tables){
    const rows=[...table.querySelectorAll('tr')];
    if(!rows.length)continue;
    const headers=[...rows[0].querySelectorAll('th,td')].map(x=>x.innerText.trim().toLowerCase());
    const idx={circa:headers.findIndex(x=>x==='circa'||x.includes('circa')),draftkings:headers.findIndex(x=>x.replace(/\s+/g,'').includes('draftkings')||x.replace(/\s+/g,'').includes('draftkings')),kalshi:headers.findIndex(x=>x.includes('kalshi'))};
    if(idx.circa<0 && idx.draftkings<0 && idx.kalshi<0)continue;
    for(const tr of rows.slice(1)){
      const cells=[...tr.querySelectorAll('th,td')];
      const rowText=cells.map(c=>c.innerText).join(' ');
      if(!wagerTeamMatch(rowText,game))continue;
      const get=(i)=>i>=0&&cells[i]?parseBookLine(cells[i].innerText):[];
      const out={};
      const c=get(idx.circa), d=get(idx.draftkings), k=get(idx.kalshi);
      if(c.length)out.circa=c;
      if(d.length)out.draftkings=d;
      if(k.length)out.kalshi=k;
      if(Object.keys(out).length)return out;
    }
  }
  return null;
}
async function fetchWagerTalkOdds(game){
  const key='wagertalk-cfb';
  if(!BIG_SKY_CIRCA_CACHE.has(key)){
    BIG_SKY_CIRCA_CACHE.set(key,(async()=>{
      try{
        const r=await fetch(WAGERTALK_CFB_URL+Date.now(),{cache:'no-store'});
        if(!r.ok)return '';
        return await r.text();
      }catch(e){ return ''; }
    })());
  }
  return extractWagerTalkBookmakers(await BIG_SKY_CIRCA_CACHE.get(key),game);
}
function sportsbookLabel(parts){ return parts.map(textOddsToken).filter(Boolean).join(' / '); }
function multiBookFormat(o){
  if(!o)return null;
  const lines=[];
  if(o.circa?.length)lines.push(`<b>CIRCA</b> ${escapeHtml(sportsbookLabel(o.circa))}`);
  if(o.draftkings?.length)lines.push(`<b>DRAFTKINGS</b> ${escapeHtml(sportsbookLabel(o.draftkings))}`);
  if(o.kalshi?.length)lines.push(`<b>KALSHI</b> ${escapeHtml(sportsbookLabel(o.kalshi))}`);
  return lines.length?{html:lines.join('<br>'),sub:'CURRENT MARKET LINES'}:null;
}

const KALSHI_CFB_EVENTS_URL='https://external-api.kalshi.com/trade-api/v2/events';
const KALSHI_CFB_CACHE = new Map();

function kalshiNormTeam(name){
  const n=bigSkyTeamKey(name);
  const aliases={
    montana:'montana',montanastate:'montanastate',
    utahtech:'utahtech',easternwashington:'easternwashington',
    idaho:'idaho',idahostate:'idahostate',
    northernarizona:'northernarizona',northerncolorado:'northerncolorado',
    portlandstate:'portlandstate',weberstate:'weberstate',
    ucdavis:'ucdavis',calpoly:'calpoly',sacramentostate:'sacramentostate',
    sacramentost:'sacramentostate'
  };
  return aliases[n]||n;
}

function kalshiEventMatches(event,game){
  const wanted=[kalshiNormTeam(game.displayAway||game.team),kalshiNormTeam(game.displayHome||game.opponent)];
  const title=bigSkyTeamKey(event?.title||'');
  const sub=bigSkyTeamKey(event?.sub_title||'');
  const hay=title+' '+sub;
  return wanted.every(w=>hay.includes(w));
}

function kalshiPrice(market){
  if(!market)return null;
  const vals=[market.last_price_dollars,market.yes_ask_dollars,market.yes_bid_dollars];
  for(const v of vals){
    const n=Number(v);
    if(Number.isFinite(n))return Math.round(n*100);
  }
  const bid=Number(market.yes_bid_dollars), ask=Number(market.yes_ask_dollars);
  if(Number.isFinite(bid)&&Number.isFinite(ask))return Math.round(((bid+ask)/2)*100);
  return null;
}

function kalshiOutcomeName(market){
  return String(market?.yes_sub_title||market?.title||'').trim();
}

function formatKalshiOdds(event,game){
  const markets=Array.isArray(event?.markets)?event.markets:[];
  if(!markets.length)return null;
  const away=kalshiNormTeam(game.displayAway||game.team), home=kalshiNormTeam(game.displayHome||game.opponent);
  const found={};
  markets.forEach(m=>{
    const name=kalshiNormTeam(kalshiOutcomeName(m));
    const price=kalshiPrice(m);
    if(price==null)return;
    if(name===away)found.away={name:game.displayAway||game.team,price};
    if(name===home)found.home={name:game.displayHome||game.opponent,price};
  });
  if(!found.away&&!found.home)return null;
  const parts=[];
  if(found.away)parts.push(`${found.away.name} ${found.away.price}%`);
  if(found.home)parts.push(`${found.home.name} ${found.home.price}%`);
  return {html:`<b>${escapeHtml(parts.join(' • '))}</b>`,sub:'KALSHI WIN PROBABILITY',url:event.event_ticker?`https://kalshi.com/events/${encodeURIComponent(event.event_ticker)}`:''};
}

async function fetchKalshiOdds(game){
  const key='ncaa-football-open';
  if(!KALSHI_CFB_CACHE.has(key)){
    KALSHI_CFB_CACHE.set(key,(async()=>{
      try{
        const url=`${KALSHI_CFB_EVENTS_URL}?series_ticker=KXNCAAFGAME&status=open&limit=1000`;
        const r=await fetch(url,{cache:'no-store'});
        if(!r.ok)return [];
        const d=await r.json();
        return Array.isArray(d.events)?d.events:[];
      }catch(e){return [];}
    })());
  }
  const events=await KALSHI_CFB_CACHE.get(key);
  const event=events.find(e=>kalshiEventMatches(e,game));
  return event?formatKalshiOdds(event,game):null;
}

async function fetchEspnCoreGameOdds(eventId, competitionId){
  if(!eventId) return null;
  const compId = competitionId || eventId;
  const urls = [
    `https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/events/${eventId}/competitions/${compId}/odds?limit=50`,
    `https://cdn.espn.com/core/college-football/game?xhr=1&gameId=${eventId}`
  ];
  for(const url of urls){
    try{
      const r=await fetch(url,{cache:'no-store'});
      if(!r.ok) continue;
      const d=await r.json();
      const items = Array.isArray(d?.items) ? d.items : [];
      const first = items[0] || d?.gamepackageJSON?.header?.competitions?.[0]?.odds?.[0] || d?.gamepackageJSON?.header?.competitions?.[0]?.odds || null;
      if(first) return first;
    }catch(e){}
  }
  return null;
}

function espnOddsMatchValue(odds){
  if(!odds) return null;
  const provider = odds.provider?.name || odds.provider?.displayName || odds.providerName || 'ESPN ODDS';
  const spread = odds.details || odds.spread || '';
  const totalValue = odds.overUnder ?? odds.total;
  const total = totalValue != null ? `O/U ${totalValue}` : '';
  const ml=[];
  const awayML = odds.awayTeamOdds?.moneyLine ?? odds.awayTeamOdds?.moneyline ?? odds.awayTeamOdds?.moneyline?.displayValue;
  const homeML = odds.homeTeamOdds?.moneyLine ?? odds.homeTeamOdds?.moneyline ?? odds.homeTeamOdds?.moneyline?.displayValue;
  if(awayML != null) ml.push(`AWAY ML ${awayML}`);
  if(homeML != null) ml.push(`HOME ML ${homeML}`);
  if(!ml.length && odds.moneyline != null){
    const v=typeof odds.moneyline==='object' ? (odds.moneyline.displayValue ?? odds.moneyline.value) : odds.moneyline;
    if(v!=null) ml.push(`ML ${v}`);
  }
  const parts=[spread,total,...ml].filter(Boolean);
  return parts.length ? {main:parts.join(' • '),sub:`ESPN${provider && provider!=='ESPN' ? ` • ${provider}`:''}`} : null;
}

function cbsWeekForDate(label){
  const m={Aug:0,Sep:1,Oct:2,Nov:3};
  const [mon,day]=String(label||'').trim().split(/\s+/);
  const dt=new Date(2026,(m[mon]??1),Number(day||1),12);
  const sep3=new Date(2026,8,3,12);
  const diff=Math.floor((dt-sep3)/86400000);
  if(dt<new Date(2026,8,3,12)) return 1;
  return Math.max(1,Math.floor(diff/7)+1);
}

function cbsTeamAliasesForOdds(name){
  const n=bigSkyTeamKey(name);
  const map={
    montana:['montana','montanagrizzlies','mont'],montanastate:['montanastate','montanastbobcats','montst','mtst'],
    utahtech:['utahtech','utahtechtrailblazers','utu'],easternwashington:['easternwashington','easternwa','ewash','ewashington'],
    southdakota:['southdakota','usd','sdak'],weberstate:['weberstate','weberst','web'],colorado:['colorado','colo'],
    northerncolorado:['northerncolorado','nco','ncol','northernco'],wyoming:['wyoming','wyo'],
    northernarizona:['northernarizona','nau','nazu','northernaz'],incarnateword:['incarnateword','uiw'],
    idahostate:['idahostate','idst'],sandiego:['sandiego','usd'],idaho:['idaho','idho'],lamar:['lamar','lam'],
    'ucdavis':['ucdavis','ucd','ucdavis'],smu:['smu'],portlandstate:['portlandstate','portlandst','post'],
    northdakota:['northdakota','ndak'],calpoly:['calpoly','cp'],sanjosestate:['sanjosestate','sjsu'],
    'coloradostate':['coloradostate','csu'],southernutah:['southernutah','sout','su'],
    nevada:['nevada','nev'],
    oregonstate:['oregonstate','orst']
  };
  return map[n] || [n];
}
function cbsGameTextMatch(text,game){
  const n=bigSkyTeamKey(text);
  const a=cbsTeamAliasesForOdds(game.displayAway||game.team), h=cbsTeamAliasesForOdds(game.displayHome||game.opponent);
  return a.some(x=>n.includes(bigSkyTeamKey(x))) && h.some(x=>n.includes(bigSkyTeamKey(x)));
}
function parseCbsOddsText(text,game){
  const clean=String(text||'').replace(/\r/g,'');
  const lines=clean.split('\n').map(x=>x.trim()).filter(Boolean);
  for(let i=0;i<lines.length;i++){
    if(!cbsGameTextMatch(lines.slice(i,i+8).join(' '),game)) continue;
    const block=lines.slice(i,Math.min(lines.length,i+12)).join(' ');
    const spreadMatches=[...block.matchAll(/([+-]\d+(?:\.5)?)(?:\s+[-+]?\d{2,3})?/g)].map(m=>m[1]);
    const mlMatches=[...block.matchAll(/([+-]\d{3,5})(?:\s+[-+]?\d{2,3})?/g)].map(m=>m[1]);
    const totalMatch=block.match(/(?:o|u)(\d+(?:\.5)?)/ig);
    const spreads=spreadMatches.filter((v,j,a)=>a.indexOf(v)===j).slice(0,2);
    const mls=mlMatches.filter((v,j,a)=>a.indexOf(v)===j).slice(0,2);
    const total=totalMatch?.[0] || '';
    if(spreads.length || mls.length || total){
      return {main:[spreads.length?`SPREAD ${spreads.join(' / ')}`:'',total?`TOTAL ${total.toUpperCase()}`:'',mls.length?`ML ${mls.join(' / ')}`:''].filter(Boolean).join(' • '),sub:'CBS SPORTS ODDS'};
    }
  }
  return null;
}
async function fetchCbsOdds(game){
  const week=cbsWeekForDate(game.date);
  const url=`https://www.cbssports.com/college-football/odds/BSKY/2026/regular/week-${week}/`;
  const proxies=[
    `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    `https://r.jina.ai/${url}`
  ];
  for(const proxy of proxies){
    try{
      const r=await fetch(proxy,{cache:'no-store'});
      if(!r.ok) continue;
      const text=await r.text();
      const found=parseCbsOddsText(text,game);
      if(found) return found;
    }catch(e){}
  }
  return null;
}

async function fetchBigSkyOdds(game){
  // The previous version depended heavily on scraping third-party HTML pages.
  // Those pages frequently block browser fetches, which made every card say
  // LINE NOT POSTED even when a line existed. ESPN's event/odds endpoints are
  // the primary source now, with CBS as a browser-safe fallback.
  const iso=bigSkyDateISO(game.date); if(!iso) return null;
  const cacheKey=iso;
  if(!BIG_SKY_ODDS_CACHE.has(cacheKey)){
    BIG_SKY_ODDS_CACHE.set(cacheKey,(async()=>{
      try{
        const ymd=iso.replaceAll('-','');
        const urls=[
          `https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${ymd}&limit=500`,
          `https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${ymd}&groups=80,81&limit=500`
        ];
        for(const u of urls){
          try{
            const res=await fetch(u,{cache:'no-store'});
            if(res.ok){const d=await res.json(); if(Array.isArray(d.events)&&d.events.length) return d.events;}
          }catch(e){}
        }
      }catch(e){}
      return [];
    })());
  }
  const events=await BIG_SKY_ODDS_CACHE.get(cacheKey);
  const ev=events.find(e=>bigSkyEventMatches(e,game));
  if(ev){
    const competition=ev.competitions?.[0];
    let odds=Array.isArray(competition?.odds)?competition.odds[0]:competition?.odds;
    const direct=espnOddsMatchValue(odds);
    if(direct) return {__allBooks:true,html:`<div class="market-line-row"><b>ESPN</b><span>${escapeHtml(direct.main)}</span></div>`,sub:direct.sub};
    const core=await fetchEspnCoreGameOdds(ev.id,competition?.id);
    const coreFormatted=espnOddsMatchValue(core);
    if(coreFormatted) return {__allBooks:true,html:`<div class="market-line-row"><b>ESPN</b><span>${escapeHtml(coreFormatted.main)}</span></div>`,sub:coreFormatted.sub};
  }
  const cbs=await fetchCbsOdds(game);
  if(cbs) return {__allBooks:true,html:`<div class="market-line-row"><b>CBS</b><span>${escapeHtml(cbs.main)}</span></div>`,sub:cbs.sub};
  return null;
}

function bigSkyWeatherLabel(code){
  const map={0:'Clear',1:'Mostly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',71:'Light snow',73:'Snow',75:'Heavy snow',80:'Rain showers',81:'Rain showers',82:'Heavy showers',85:'Snow showers',86:'Heavy snow showers',95:'Thunderstorms',96:'T-storms + hail',99:'T-storms + hail'};
  return map[Number(code)] || 'Forecast';
}
function forecastOpenDate(gameDate){
  const dt=new Date(`${gameDate}T12:00:00`);
  dt.setDate(dt.getDate()-7);
  return dt.toLocaleDateString('en-US',{month:'short',day:'numeric'});
}
async function fetchBigSkyWeather(game){
  const iso=bigSkyDateISO(game.date); const v=bigSkyVenueFor(game); if(!iso||!v) return null;
  const key=`${iso}|${v.lat}|${v.lon}`;
  if(!BIG_SKY_WEATHER_CACHE.has(key)){
    BIG_SKY_WEATHER_CACHE.set(key,(async()=>{
      try{
        // Ask Open-Meteo for its full available forecast window instead of
        // requesting a single date. This prevents future games from being
        // incorrectly labeled TBD when the forecast is available.
        const url=`https://api.open-meteo.com/v1/forecast?latitude=${v.lat}&longitude=${v.lon}&daily=weather_code,temperature_2m_max,precipitation_probability_max,wind_speed_10m_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=16`;
        const res=await fetch(url,{cache:'no-store'}); if(!res.ok) return {available:false,openDate:forecastOpenDate(iso)};
        const d=await res.json();
        const idx=Array.isArray(d.daily?.time)?d.daily.time.indexOf(iso):-1;
        if(idx<0) return {available:false,openDate:forecastOpenDate(iso),venue:v.venue};
        return {available:true,temp:d.daily.temperature_2m_max?.[idx],code:d.daily.weather_code?.[idx],rain:d.daily.precipitation_probability_max?.[idx],wind:d.daily.wind_speed_10m_max?.[idx],venue:v.venue};
      }catch(e){ return {available:false,openDate:forecastOpenDate(iso),venue:v.venue}; }
    })());
  }
  return await BIG_SKY_WEATHER_CACHE.get(key);
}
async function enrichBigSkyScheduleCards(schedule){
  const jobs=schedule.map(async game=>{
    const key=`${game.date}|${game.team}|${game.opponent}|${game.location||''}`;
    const row=document.querySelector(`.bigsky-game-card[data-bigsky-game-key="${CSS.escape(key)}"]`);
    if(!row) return;
    const [odds,weather]=await Promise.all([fetchBigSkyOdds(game),fetchBigSkyWeather(game)]);
    const bet=row.querySelector('.bigsky-betting');
    const wx=row.querySelector('.bigsky-weather');
    const o=odds?.__allBooks ? odds : (odds?.__multi ? odds : (odds?.__circa ? (circaFormatOdds(odds) || bigSkyFormatOdds(odds)) : bigSkyFormatOdds(odds)));
    if(bet){ if(o?.html) bet.innerHTML=`${o.html}<small>${escapeHtml(o.sub||'CURRENT MARKET LINES')}</small>`; else bet.innerHTML=`<b>${escapeHtml(o?.main||'LINE NOT POSTED')}</b><small>${escapeHtml(o?.sub||'BETTING LINE')}</small>`; }
    if(wx){
      if(weather?.available){
        const temp=weather.temp!=null?`${Math.round(weather.temp)}°`:'—';
        const rain=weather.rain!=null?`${Math.round(weather.rain)}% rain`:'';
        const wind=weather.wind!=null?`${Math.round(weather.wind)} mph wind`:'';
        wx.innerHTML=`<b>${escapeHtml(temp)} • ${escapeHtml(bigSkyWeatherLabel(weather.code))}</b><small>${escapeHtml([rain,wind].filter(Boolean).join(' • ')||'Forecast')}</small>`;
      }else if(weather?.openDate){
        wx.innerHTML=`<b>FORECAST OPENS ${escapeHtml(weather.openDate).toUpperCase()}</b><small>WEATHER NOT YET IN FORECAST WINDOW</small>`;
      }else{
        wx.innerHTML='<b>FORECAST UNAVAILABLE</b><small>TRY AGAIN LATER</small>';
      }
    }
  });
  await Promise.all(jobs);
}


const BIG_SKY_LOGOS={
  'Montana':'https://a.espncdn.com/i/teamlogos/ncaa/500/149.png',
  'Montana State':'https://a.espncdn.com/i/teamlogos/ncaa/500/147.png',
  'Idaho':'https://a.espncdn.com/i/teamlogos/ncaa/500/70.png',
  'Idaho State':'https://a.espncdn.com/i/teamlogos/ncaa/500/304.png',
  'Eastern Washington':'https://a.espncdn.com/i/teamlogos/ncaa/500/331.png',
  'Northern Arizona':'https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png',
  'Northern Colorado':'https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png',
  'Portland State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2502.png',
  'Sacramento State':'https://a.espncdn.com/i/teamlogos/ncaa/500/16.png',
  'Weber State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2692.png',
  'UC Davis':'https://a.espncdn.com/i/teamlogos/ncaa/500/302.png',
  'Cal Poly':'https://a.espncdn.com/i/teamlogos/ncaa/500/13.png',
  'Utah Tech':'https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png',
  'Oregon State':'https://a.espncdn.com/i/teamlogos/ncaa/500/204.png',
  'Washington State':'https://a.espncdn.com/i/teamlogos/ncaa/500/265.png',
  'Oregon':'https://a.espncdn.com/i/teamlogos/ncaa/500/2483.png',
  'Colorado':'https://a.espncdn.com/i/teamlogos/ncaa/500/38.png',
  'SMU':'https://a.espncdn.com/i/teamlogos/ncaa/500/256.png',
  'San Diego':'https://a.espncdn.com/i/teamlogos/ncaa/500/301.png',
  'Southern Utah':'https://a.espncdn.com/i/teamlogos/ncaa/500/253.png',
  'Lamar':'https://a.espncdn.com/i/teamlogos/ncaa/500/2320.png',
  'South Dakota':'https://a.espncdn.com/i/teamlogos/ncaa/500/233.png',
  'Wyoming':'https://a.espncdn.com/i/teamlogos/ncaa/500/2751.png',
  'Incarnate Word':'https://a.espncdn.com/i/teamlogos/ncaa/500/2916.png',
  'Colorado State':'https://a.espncdn.com/i/teamlogos/ncaa/500/36.png',
  'San Jose State':'https://a.espncdn.com/i/teamlogos/ncaa/500/23.png',
  'North Dakota':'https://a.espncdn.com/i/teamlogos/ncaa/500/155.png',
  'Nevada':'https://a.espncdn.com/i/teamlogos/ncaa/500/2440.png'
};
function bigSkyLogo(name){
  if(BIG_SKY_LOGOS[name]) return BIG_SKY_LOGOS[name];
  const key=String(name||'').trim().toLowerCase();
  const found=Object.keys(BIG_SKY_LOGOS).find(k=>k.toLowerCase()===key);
  return found?BIG_SKY_LOGOS[found]:'';
}
function bigSkyTeamMarkup(name,record,side){
  const logo=bigSkyLogo(name);
  return `<div class="bigsky-team ${side}">${logo?`<img class="bigsky-team-logo" src="${logo}" alt="${escapeHtml(name)} logo" loading="lazy" onerror="this.style.display='none'">`:''}<div class="bigsky-team-copy"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(record||'')}</small></div></div>`;
}

const MADDUX_CFB_URL='https://madduxsports.com/college-football-lines.php';
const MADDUX_CFB_CACHE=new Map();
function madduxAliases(name){
  const n=bigSkyTeamKey(name);
  const map={
    montana:['montana','montanagrizzlies'],montanastate:['montanastate','montanastbobcats','montanastatebobcats'],
    easternwashington:['easternwashington','easternwashingtoneagles','easternwa'],idaho:['idaho','idahovandals'],idahostate:['idahostate','idahobengals'],
    northernarizona:['northernarizona','northernaz','nau'],northerncolorado:['northerncolorado','northernco'],portlandstate:['portlandstate','portlandst'],
    sacramentostate:['sacramentostate','sacramento','sacstate'],weberstate:['weberstate','weberst'],ucdavis:['ucdavis','ucd'],calpoly:['calpoly'],
    utahtech:['utahtech','utahtechtrailblazers']
  };
  return map[n]||[n];
}
function madduxGameMatch(text,game){
  const n=bigSkyTeamKey(text);
  const a=madduxAliases(game.displayAway||game.team), h=madduxAliases(game.displayHome||game.opponent);
  return a.some(x=>n.includes(x))&&h.some(x=>n.includes(x));
}
function parseMadduxBooks(html,game){
  if(!html)return null;
  const doc=new DOMParser().parseFromString(html,'text/html');
  const tables=[...doc.querySelectorAll('table')];
  const wanted=['circa','draftkings','betonline','pinnacle','bovada','betmgm','fanduel','bet365','caesars'];
  for(const table of tables){
    const rows=[...table.querySelectorAll('tr')]; if(!rows.length)continue;
    const header=[...rows[0].querySelectorAll('th,td')].map(c=>bigSkyTeamKey(c.innerText));
    const idx={}; wanted.forEach(w=>{const i=header.findIndex(h=>h.includes(bigSkyTeamKey(w)));if(i>=0)idx[w]=i;});
    if(!Object.keys(idx).length)continue;
    for(const tr of rows.slice(1)){
      const cells=[...tr.querySelectorAll('th,td')]; const rowText=cells.map(c=>c.innerText).join(' ');
      if(!madduxGameMatch(rowText,game))continue;
      const out={};
      Object.entries(idx).forEach(([book,i])=>{const val=(cells[i]?.innerText||'').replace(/\s+/g,' ').trim();if(val&&val!=='-')out[book]=val;});
      if(Object.keys(out).length)return out;
    }
  }
  return null;
}
async function fetchMadduxOdds(game){
  const key='maddux-cfb';
  if(!MADDUX_CFB_CACHE.has(key)){
    MADDUX_CFB_CACHE.set(key,(async()=>{try{const r=await fetch(MADDUX_CFB_URL,{cache:'no-store'});if(!r.ok)return '';return await r.text();}catch(e){return '';}})());
  }
  return parseMadduxBooks(await MADDUX_CFB_CACHE.get(key),game);
}
function mergeMarketLines(base,more){
  const out={...(base||{})};
  Object.entries(more||{}).forEach(([k,v])=>{if(v&&(!out[k]||String(out[k]).length<String(v).length))out[k]=v;});
  return out;
}
function formatAllBookLines(kalshi,multi,maddux,circa){
  const rows=[];
  if(kalshi?.html) rows.push(`<div class="market-line-row kalshi-line"><b>KALSHI</b><span>${kalshi.html.replace(/<\/?b>/g,'')}</span></div>`);
  const merged=mergeMarketLines(multi,maddux);
  const labels={circa:'CIRCA',draftkings:'DRAFTKINGS',betonline:'BETONLINE',pinnacle:'PINNACLE',bovada:'BOVADA',betmgm:'BETMGM',fanduel:'FANDUEL',bet365:'BET365',caesars:'CAESARS'};
  Object.entries(labels).forEach(([key,label])=>{if(merged?.[key])rows.push(`<div class="market-line-row"><b>${label}</b><span>${escapeHtml(String(merged[key]))}</span></div>`);});
  if(circa && !merged?.circa){const bits=[circa.spread,circa.total,circa.moneyline].filter(Boolean).join(' • ');if(bits)rows.push(`<div class="market-line-row"><b>CIRCA</b><span>${escapeHtml(bits)}</span></div>`);}
  if(!rows.length)return null;
  return {html:rows.join(''),sub:'LINE SHOP • MULTIPLE SOURCES'};
}

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
        const visible = [];
        const seen = new Set();

        // Build one card per matchup when viewing the whole league.  The source
        // schedule contains a row for each participating team, so dedupe games
        // here without changing the underlying data or any other site section.
        shownTeams.forEach(team => {
          weekGames.filter(game => game.team === team).forEach(game => {
            const a = game.location === "Away" ? game.team : game.opponent;
            const h = game.location === "Away" ? game.opponent : game.team;
            const matchupKey = `${game.date}|${a}|${h}|${game.time || ""}`;
            if (selectedTeam === "ALL" && seen.has(matchupKey)) return;
            seen.add(matchupKey);
            visible.push({...game, displayAway:a, displayHome:h, matchupKey});
          });
        });

        visible.sort((a,b) => dateObj(a.date) - dateObj(b.date) || String(a.time||"").localeCompare(String(b.time||"")) || a.displayAway.localeCompare(b.displayAway));

        const dateLabel = label => {
          const dt = dateObj(label);
          return dt.toLocaleDateString("en-US", {weekday:"long", month:"long", day:"numeric"}).toUpperCase();
        };
        const rows = [];
        let lastDate = "";
        visible.forEach(game => {
          if (game.date !== lastDate) {
            rows.push(`<div class="bigsky-date-divider"><span>${escapeHtml(dateLabel(game.date))}</span></div>`);
            lastDate = game.date;
          }
          const prefix = game.location === "Away" ? "AWAY" : "HOME";
          const tag = game.big_sky_game ? '<span class="league-tag">BIG SKY</span>' : '<span class="league-tag nonconf-tag">NON-CONFERENCE</span>';
          const key = `${game.date}|${game.team}|${game.opponent}|${game.location || ""}`;
          rows.push(`<div class="bigsky-game-card" data-bigsky-game-key="${escapeHtml(key)}">
            <div class="bigsky-game-top">
              <div class="bigsky-game-time"><strong>${escapeHtml(game.time || "TBA")}</strong><span>${escapeHtml(game.network || "")}</span></div>
              <div class="bigsky-game-type">${tag}<span>${escapeHtml(prefix)}</span></div>
            </div>
            <div class="bigsky-matchup">
              ${bigSkyTeamMarkup(game.displayAway, game.displayAway === game.team ? (game.away_record || "") : (game.opponent_record || ""), "away")}
              <div class="bigsky-at">@</div>
              ${bigSkyTeamMarkup(game.displayHome, game.displayHome === game.team ? (game.home_record || "") : (game.opponent_record || ""), "home")}
            </div>
            <div class="bigsky-game-bottom">
              <div class="bigsky-location"><b>${escapeHtml(game.venue || (game.location === "Away" ? "Away Game" : "Home Game"))}</b><span>${escapeHtml(game.city || "")}</span></div>
              <div class="bigsky-info bigsky-betting"><b>CHECKING…</b><small>MARKET LINES</small></div>
              <div class="bigsky-info bigsky-weather"><b>CHECKING…</b><small>GAME WEATHER</small></div>
            </div>
          </div>`);
        });

        if (!visible.length) {
          rows.push(`<div class="bigsky-empty"><b>NO GAMES THIS WEEK</b><span>${escapeHtml(selectedTeam === "ALL" ? "No Big Sky matchups are scheduled." : `${selectedTeam} has a bye.`)}</span></div>`);
        }

        table.innerHTML = rows.join("");

        // Enrich only the games currently visible in the selected week/team view.
        // The existing ESPN/weather calls remain isolated to this Big Sky section.
        enrichBigSkyScheduleCards(visible);
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
  if(!weekEl.dataset.ready){
    weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});
    weekEl.dataset.ready='1';
  }
  function getCurrentFootballWeek(){
    const today=new Date();
    const day=new Date(today.getFullYear(),today.getMonth(),today.getDate(),12);
    const inside=weeks.findIndex(w=>day>=new Date(w[0]+'T12:00:00')&&day<=new Date(w[1]+'T12:00:00'));
    if(inside>=0)return inside;
    const next=weeks.findIndex(w=>new Date(w[0]+'T12:00:00')>day);
    return next>=0?next:weeks.length-1;
  }
  if(!weekEl.dataset.userChanged) weekEl.value=String(getCurrentFootballWeek());

  let localData={};
  try{localData=await (await fetch('data.json?ts='+Date.now(),{cache:'no-store'})).json();}
  catch(e){if(statusEl)statusEl.textContent='Score data unavailable';return;}

  const top25=Array.isArray(localData.fcs_top25)?localData.fcs_top25:(Array.isArray(localData.fcs_top20)?localData.fcs_top20:[]);
  const fullSchedule=Array.isArray(localData.big_sky_full_schedules)?localData.big_sky_full_schedules:[];
  const cachedScores=localData.fcs_scores&&typeof localData.fcs_scores==='object'?localData.fcs_scores:{};
  const rankDate=document.getElementById('fcs-rankings-date');
  if(rankDate&&localData.fcs_rankings_date) rankDate.textContent='Stats Perform • '+localData.fcs_rankings_date;

  function cleanTeamLabel(s){return String(s||'').replace(/\s*\([^)]*\)\s*$/,'').replace(/\s+/g,' ').trim();}
  function norm(s){return cleanTeamLabel(s).toLowerCase().replace(/[^a-z0-9]/g,'');}
  const teamIds={montana:'149',montanastate:'147',idaho:'70',weberstate:'2692',easternwashington:'331',northernarizona:'2464',northerncolorado:'2458',idahostate:'304',calpoly:'13',southernutah:'253',utahtech:'3101',ucdavis:'302',portlandstate:'2502'};
  const FCS_LOGO_IDS={
    Montana:'149','Montana State':'147',Idaho:'70','Weber State':'2692','Eastern Washington':'331','Northern Arizona':'2464','Northern Colorado':'2458','Idaho State':'304','Cal Poly':'13','Southern Utah':'253','Utah Tech':'3101','UC Davis':'302','Portland State':'2502',
    Nevada:'2440',Colorado:'38','South Dakota':'233','Wyoming':'2751','Colorado State':'36',Utah:'254',Oregon:'2483','Oregon State':'204','Washington State':'265',Washington:'264','San Jose State':'23','San José State':'23','Utah State':'328','Boise State':'68','Fresno State':'278','San Diego State':'21','South Dakota State':'2569','North Dakota State':'2449','Montana State (57)':'147','North Dakota':'155','Lamar':'2320','Incarnate Word':'2916','SMU':'256', 'San Diego':'301','Yale':'43','West Florida':'290','Harvard':'108'
  };
  const bigSkyAliases={
    montana:['montana','montanagrizzlies'],montanastate:['montanastate','montanast','montanastatebobcats'],idaho:['idaho','idahovandals'],
    weberstate:['weberstate','weberst','weberstatewildcats'],easternwashington:['easternwashington','ewashington','easternwash','easternwashingtoneagles'],
    northernarizona:['northernarizona','narizona','northernaz','northernarizonalumberjacks'],northerncolorado:['northerncolorado','ncolorado','northerncoloradobears'],
    idahostate:['idahostate','idahost','idst','idahostatebengals'],calpoly:['calpoly','calpolytechnic','calpolymustangs'],
    southernutah:['southernutah','soutah','soututah','southernutahthunderbirds'],utahtech:['utahtech','utahtechuniversity','utahtechtrailblazers'],
    ucdavis:['ucdavis','ucdavisaggies'],portlandstate:['portlandstate','portlandst','portlandstatevikings']
  };
  function canonicalBigSky(s){const n=norm(s);for(const [k,v] of Object.entries(bigSkyAliases))if(v.some(x=>norm(x)===n))return k;return null;}
  function teamMatch(a,b){
    if(!a||!b)return false;
    const ao=typeof a==='object'?a:null,bo=typeof b==='object'?b:null;
    if(ao?.id&&bo?.id&&String(ao.id)===String(bo.id))return true;
    const an=norm(ao?.displayName||ao?.name||ao?.short||ao?.shortDisplayName||ao?.abbrev||a);
    const bn=norm(bo?.displayName||bo?.name||bo?.short||bo?.shortDisplayName||bo?.abbrev||b);
    if(!an||!bn)return false;
    if(an===bn)return true;
    const ac=canonicalBigSky(an),bc=canonicalBigSky(bn);
    if(ac&&bc&&ac===bc)return true;
    // General FCS school-name matching. ESPN often appends the mascot;
    // rankings normally do not.  The Montana/Montana State guard prevents
    // the shorter Montana name from matching the Bobcats.
    const protectedPairs=[['montana','montanastate'],['idaho','idahostate'],['southdakota','southdakotastate'],['northdakota','northdakotastate']];
    const protectedPair=protectedPairs.some(([x,y])=>(an===x&&bn===y)||(an===y&&bn===x));
    if(!protectedPair && (an.startsWith(bn)||bn.startsWith(an)))return true;
    return false;
  }
  function teamObjMatch(name,t){
    if(!t)return false;
    const key=canonicalBigSky(name)||norm(name);
    if(t.id&&teamIds[key]&&String(t.id)===String(teamIds[key]))return true;
    return teamMatch(name,t.displayName||t.name||t.shortDisplayName||t.short||t.abbreviation||'');
  }
  function eventTeams(ev){return Array.isArray(ev?.teams)?ev.teams:[];}
  function logoIdForName(name){
    const cleaned=cleanTeamLabel(name);
    if(FCS_LOGO_IDS[cleaned])return FCS_LOGO_IDS[cleaned];
    const key=canonicalBigSky(cleaned);
    if(key&&teamIds[key])return teamIds[key];
    const n=norm(cleaned);
    const hit=Object.entries(FCS_LOGO_IDS).find(([k])=>norm(k)===n);
    return hit?hit[1]:'';
  }
  function logoFor(t,fallback=''){
    const id=t?.team?.id||t?.id;
    return t?.team?.logo||t?.logo||(id?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(id)}.png`:logoIdForName(fallback)?`https://a.espncdn.com/i/teamlogos/ncaa/500/${logoIdForName(fallback)}.png`:'');
  }
  function teamName(t,fallback='Team'){return t?.shortDisplayName||t?.short||t?.displayName||t?.name||t?.abbreviation||fallback;}
  function scheduleDate(label){
    const m={Aug:7,Sep:8,Oct:9,Nov:10};
    const [mo,day]=String(label||'').trim().split(/\s+/);
    return mo&&m[mo]!=null&&day?new Date(2026,m[mo],Number(day),12):null;
  }
  function scheduleGamesForWeek(w){
    const start=new Date(w[0]+'T00:00:00'),end=new Date(w[1]+'T23:59:59');
    const byGame=new Map();
    fullSchedule.forEach(g=>{
      const dt=scheduleDate(g.date);if(!dt||dt<start||dt>end)return;
      const bs=canonicalBigSky(g.team);
      if(!bs)return;
      const away=g.location==='Away'?g.opponent:g.team;
      const home=g.location==='Away'?g.team:g.opponent;
      if(!away||!home)return;
      const pair=[norm(away),norm(home)].sort().join('|'); const key=`${String(g.date)}|${pair}`;
      const existing=byGame.get(key);
      if(existing){
        existing.bigSkyGame=existing.bigSkyGame||!!g.big_sky_game;
        if((!existing.time||existing.time==='TBA')&&g.time)existing.time=g.time;
        if(!existing.network&&g.network)existing.network=g.network;
        return;
      }
      byGame.set(key,{...g,date:g.date,time:g.time||'TBA',displayAway:away,displayHome:home,bigSkyGame:!!g.big_sky_game,matchupKey:key});
    });
    return [...byGame.values()].sort((a,b)=>{
      const da=scheduleDate(a.date)?.getTime()||0,db=scheduleDate(b.date)?.getTime()||0;
      return da-db||String(a.time||'').localeCompare(String(b.time||''));
    });
  }
  function normalizeEvent(ev){
    const c=(ev?.competitions||[])[0]||{};
    const teams=(c.competitors||[]).map(x=>({id:String(x.id||x.team?.id||''),name:x.team?.displayName||'',short:x.team?.shortDisplayName||x.team?.displayName||'',abbreviation:x.team?.abbreviation||'',homeAway:x.homeAway||'',score:x.score??'',logo:x.team?.logo||'',team:x.team||{}}));
    const st=c.status?.type||{};const broadcasts=[];(c.broadcasts||[]).forEach(b=>(b.names||[]).forEach(n=>broadcasts.push(n)));
    const odds=Array.isArray(c.odds)?c.odds[0]:(c.odds||null);
    return {id:String(ev.id||''),date:ev.date||c.date||'',teams,state:st.state||'',completed:!!st.completed,detail:st.shortDetail||st.detail||'',broadcasts:broadcasts.slice(0,3),odds,raw:ev};
  }
  function eventMatchesGame(ev,g){
    const ts=eventTeams(ev);if(ts.length<2)return false;
    const a=ts.find(t=>t.homeAway==='away')||ts[0],h=ts.find(t=>t.homeAway==='home')||ts[1];
    return teamMatch(g.displayAway,a)&&teamMatch(g.displayHome,h);
  }
  function findTeamEvent(team,events){return events.find(ev=>eventTeams(ev).some(t=>teamObjMatch(team,t)))||null;}
  const HISTORICAL_BIG_SKY_SCORES={
    '2026-09-05':[
      {id:'ghq-w1-montana-suu',date:'2026-09-05T19:00:00Z',teams:[{id:'253',name:'Southern Utah',short:'Southern Utah',abbreviation:'SUU',homeAway:'away',score:'21',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/253.png',team:{displayName:'Southern Utah',shortDisplayName:'Southern Utah',abbreviation:'SUU'}},{id:'149',name:'Montana',short:'Montana',abbreviation:'MONT',homeAway:'home',score:'28',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/149.png',team:{displayName:'Montana',shortDisplayName:'Montana',abbreviation:'MONT'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-idst-vmi',date:'2026-09-05T18:00:00Z',teams:[{id:'261',name:'VMI',short:'VMI',abbreviation:'VMI',homeAway:'away',score:'10',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/2678.png',team:{displayName:'VMI',shortDisplayName:'VMI',abbreviation:'VMI'}},{id:'304',name:'Idaho State',short:'Idaho State',abbreviation:'IDST',homeAway:'home',score:'38',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/304.png',team:{displayName:'Idaho State',shortDisplayName:'Idaho State',abbreviation:'IDST'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-ucd-psu',date:'2026-09-05T22:00:00Z',teams:[{id:'302',name:'UC Davis',short:'UC Davis',abbreviation:'UCD',homeAway:'away',score:'31',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/302.png',team:{displayName:'UC Davis',shortDisplayName:'UC Davis',abbreviation:'UCD'}},{id:'279',name:'Portland State',short:'Portland State',abbreviation:'PSU',homeAway:'home',score:'24',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/279.png',team:{displayName:'Portland State',shortDisplayName:'Portland State',abbreviation:'PSU'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-ewu-nau',date:'2026-09-05T21:00:00Z',teams:[{id:'331',name:'Eastern Washington',short:'Eastern Washington',abbreviation:'EWU',homeAway:'away',score:'27',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/331.png',team:{displayName:'Eastern Washington',shortDisplayName:'Eastern Washington',abbreviation:'EWU'}},{id:'2464',name:'Northern Arizona',short:'Northern Arizona',abbreviation:'NAU',homeAway:'home',score:'34',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png',team:{displayName:'Northern Arizona',shortDisplayName:'Northern Arizona',abbreviation:'NAU'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-msu-utu',date:'2026-09-05T20:00:00Z',teams:[{id:'3101',name:'Utah Tech',short:'Utah Tech',abbreviation:'UTU',homeAway:'away',score:'0',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png',team:{displayName:'Utah Tech',shortDisplayName:'Utah Tech',abbreviation:'UTU'}},{id:'147',name:'Montana State',short:'Montana State',abbreviation:'MONT',homeAway:'home',score:'54',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/147.png',team:{displayName:'Montana State',shortDisplayName:'Montana State',abbreviation:'MONT'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-weber-unc',date:'2026-09-05T19:00:00Z',teams:[{id:'2692',name:'Weber State',short:'Weber State',abbreviation:'WEB',homeAway:'away',score:'30',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/2692.png',team:{displayName:'Weber State',shortDisplayName:'Weber State',abbreviation:'WEB'}},{id:'2458',name:'Northern Colorado',short:'Northern Colorado',abbreviation:'UNC',homeAway:'home',score:'29',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png',team:{displayName:'Northern Colorado',shortDisplayName:'Northern Colorado',abbreviation:'UNC'}}],state:'post',completed:true,detail:'Final',broadcasts:[]},
      {id:'ghq-w1-idaho-calpoly',date:'2026-09-05T19:00:00Z',teams:[{id:'70',name:'Idaho',short:'Idaho',abbreviation:'IDAH',homeAway:'away',score:'34',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/70.png',team:{displayName:'Idaho',shortDisplayName:'Idaho',abbreviation:'IDAH'}},{id:'13',name:'Cal Poly',short:'Cal Poly',abbreviation:'CP',homeAway:'home',score:'38',logo:'https://a.espncdn.com/i/teamlogos/ncaa/500/13.png',team:{displayName:'Cal Poly',shortDisplayName:'Cal Poly',abbreviation:'CP'}}],state:'post',completed:true,detail:'Final',broadcasts:[]}
    ]
  };
  function historicalScoresForWeek(w){
    const out=[];
    Object.entries(HISTORICAL_BIG_SKY_SCORES).forEach(([date,items])=>{if(date>=w[0]&&date<=w[1])out.push(...items);});
    return out;
  }
  function cachedEventsForWeek(w){
    const out=[...historicalScoresForWeek(w)];Object.entries(cachedScores).forEach(([date,items])=>{if(date>=w[0]&&date<=w[1]&&Array.isArray(items))out.push(...items);});
    const seen=new Set();return out.filter(ev=>{const k=String(ev.id||'')||JSON.stringify(ev);if(seen.has(k))return false;seen.add(k);return true;});
  }
  async function fetchESPNEvents(w){
    const urls=[
      `https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${w[0]}-${w[1]}&groups=81&limit=1000`,
      `https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${w[0]}-${w[1]}&limit=1000`,
      `https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${w[0]}-${w[1]}&groups=81&limit=1000`,
      `https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${w[0]}-${w[1]}&limit=1000`
    ];
    const all=[]; const seen=new Set();
    for(const url of urls){try{const r=await fetch(url,{cache:'no-store'});if(!r.ok)continue;const p=await r.json();for(const ev of (Array.isArray(p.events)?p.events:[])){const id=String(ev.id||'');if(id&&!seen.has(id)){seen.add(id);all.push(ev);}}}catch(e){}}
    return all;
  }
  function statusText(ev,game){
    if(!ev)return game?.time||'TBA';
    if(ev.completed)return ev.detail||'FINAL';
    if(ev.state==='in')return ev.detail||'LIVE';
    return game?.time|| (ev.date?new Date(ev.date).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'TBA');
  }
  function scoreCardTeam(t,fallback,showScore){
    const name=teamName(t,fallback),logo=logoFor(t,fallback);
    return `<div class="score-team-row ghq-fcs-team-row">${logo?`<img src="${escapeHtml(logo)}" alt="" loading="lazy" onerror="this.style.display='none'">`:''}<span>${escapeHtml(name)}</span>${showScore?`<strong>${escapeHtml(t?.score??'—')}</strong>`:''}</div>`;
  }
  function top25TeamRow(t, fallback, rank, isRanked, showScore){
    const name=teamName(t,fallback), logo=logoFor(t,fallback);
    const rankHtml=isRanked?`<span class="fcs-team-rank">#${escapeHtml(rank)}</span>`:'<span class="fcs-team-rank fcs-team-rank-empty"></span>';
    const logoHtml=`<span class="ghq-fcs-top-logo-slot">${logo?`<img src="${escapeHtml(logo)}" alt="" loading="lazy" onerror="this.style.display='none'">`:''}</span>`;
    return `<div class="ghq-fcs-top-team-row">${rankHtml}${logoHtml}<span>${escapeHtml(name)}</span>${showScore?`<strong>${escapeHtml(t?.score??'—')}</strong>`:''}</div>`;
  }
  function top25Card(t,events,scheduled){
    const rank=String(t.rank||''),name=cleanTeamLabel(t.team||'Team');
    const sg=scheduled.find(g=>teamMatch(name,g.displayAway)||teamMatch(name,g.displayHome)) || fullSchedule.map(g=>{ const dt=scheduleDate(g.date); const start=new Date(weeks[Number(weekEl.value)||0][0]+'T00:00:00'); const end=new Date(weeks[Number(weekEl.value)||0][1]+'T23:59:59'); if(!dt||dt<start||dt>end)return null; const away=g.location==='Away'?g.opponent:g.team; const home=g.location==='Away'?g.team:g.opponent; return {...g,displayAway:away,displayHome:home,matchupKey:`${g.date}|${[norm(away),norm(home)].sort().join('|')}`}; }).find(g=>g && (teamMatch(name,g.displayAway)||teamMatch(name,g.displayHome)));
    const rawEv=findTeamEvent(name,events);
    const ev=sg ? (events.find(e=>eventMatchesGame(e,sg)) || rawEv && eventMatchesGame(rawEv,sg) ? (events.find(e=>eventMatchesGame(e,sg)) || rawEv) : null) : rawEv;
    if(ev){
      const ts=eventTeams(ev);
      const a=sg? (ts.find(x=>teamMatch(sg.displayAway,x))||ts.find(x=>x.homeAway==='away')||ts[0]) : (ts.find(x=>x.homeAway==='away')||ts[0]);
      const h=sg? (ts.find(x=>teamMatch(sg.displayHome,x))||ts.find(x=>x.homeAway==='home')||ts.find(x=>x!==a)||ts[1]) : (ts.find(x=>x.homeAway==='home')||ts.find(x=>x!==a)||ts[1]);
      const playing=ev.completed||ev.state==='in';
      const rankedAway=teamMatch(name,a), rankedHome=teamMatch(name,h);
      const awayRow=top25TeamRow(a,sg?.displayAway||'Away',rank,rankedAway,playing);
      const homeRow=top25TeamRow(h,sg?.displayHome||'Home',rank,rankedHome,playing);
      return `<div class="fcs-rank-card ghq-fcs-rank-card"><div class="ghq-fcs-top-scorecard">${awayRow}${homeRow}<div class="ghq-fcs-top-meta"><span>${escapeHtml(statusText(ev,sg))}</span>${ev?.broadcasts?.length?`<small>${escapeHtml(ev.broadcasts.slice(0,2).flatMap(b=>b.names||[]).join(', '))}</small>`:''}</div></div></div>`;
    }
    if(sg){
      const rankedAway=teamMatch(name,sg.displayAway), rankedHome=teamMatch(name,sg.displayHome);
      return `<div class="fcs-rank-card ghq-fcs-rank-card"><div class="ghq-fcs-top-scorecard">${top25TeamRow(null,sg.displayAway,rank,rankedAway,false)}${top25TeamRow(null,sg.displayHome,rank,rankedHome,false)}<div class="ghq-fcs-top-meta"><span>${escapeHtml(sg.time||'TBA')}</span>${sg.network?`<small>${escapeHtml(sg.network)}</small>`:''}</div></div></div>`;
    }
    return `<div class="fcs-rank-card ghq-fcs-rank-card"><div class="ghq-fcs-top-scorecard">${top25TeamRow(null,name,rank,true,false)}<div class="ghq-fcs-top-meta"><span>BYE / NO GAME THIS WEEK</span></div></div></div>`;
  }
  function gameCard(game,ev){
    const ts=eventTeams(ev);
    // Always honor the scheduled matchup's home/away designation. ESPN can
    // return competitors in different orders, and some historical/cached
    // events do not reliably preserve homeAway. The scoreboard convention is
    // therefore: AWAY team on top, HOME team on bottom.
    const scheduledAway=game.displayAway,scheduledHome=game.displayHome;
    const a=ts.find(x=>teamMatch(scheduledAway,x))||ts.find(x=>x.homeAway==='away')||ts[0]||null;
    const h=ts.find(x=>teamMatch(scheduledHome,x))||ts.find(x=>x.homeAway==='home')||ts.find(x=>x!==a)||null;
    const final=!!ev?.completed,live=ev?.state==='in',state=live?'live':(final?'final':'scheduled');
    const label=game.bigSkyGame?'BIG SKY':'NON-CONFERENCE';
    const tv=(ev?.broadcasts||[]).slice(0,2).join(', ');
    const status=statusText(ev,game);
    const awayName=a?teamName(a,scheduledAway):scheduledAway;
    const homeName=h?teamName(h,scheduledHome):scheduledHome;
    return `<div class="fcs-game ${state} bigsky-row ghq-fcs-game" data-fcs-game-key="${escapeHtml(game.matchupKey)}"><div class="fcs-time"><b>${escapeHtml(game.date)}</b><small>${escapeHtml(label)}</small></div><div class="fcs-matchup">${scoreCardTeam(a,awayName,final||live)}${scoreCardTeam(h,homeName,final||live)}<small class="score-game-status">${escapeHtml(status)}${tv?' • '+escapeHtml(tv):''}</small></div><div class="fcs-score score-status">${final||live?`<span class="score-big">${escapeHtml(a?.score??'—')}–${escapeHtml(h?.score??'—')}</span><small>${escapeHtml(final?'FINAL':status)}</small>`:`<small>${escapeHtml(status)}</small>`}</div><div class="fcs-tv">${escapeHtml(tv)}</div><div class="bigsky-info bigsky-betting"><b>CHECKING…</b><small>MARKET LINES</small></div></div>`;
  }
  function liveOrCachedForGame(game,liveEvents,cachedEvents){
    return liveEvents.find(e=>eventMatchesGame(e,game))||cachedEvents.find(e=>{const ts=eventTeams(e);return ts.some(t=>teamMatch(game.displayAway,t))&&ts.some(t=>teamMatch(game.displayHome,t));})||null;
  }
  async function enrichScoreCards(games,normalizedLive){
    await Promise.all(games.map(async game=>{
      const row=[...document.querySelectorAll('.ghq-fcs-game[data-fcs-game-key]')].find(el=>el.dataset.fcsGameKey===game.matchupKey);if(!row)return;
      const live=normalizedLive.find(e=>eventMatchesGame(e,game));
      try{
        let odds=null;
        if(live?.odds){const f=espnOddsMatchValue(live.odds);if(f)odds={__allBooks:true,html:`<div class="market-line-row"><b>ESPN</b><span>${escapeHtml(f.main)}</span></div>`,sub:f.sub};}
        if(!odds) odds=await fetchBigSkyOdds({...game,team:game.displayAway,opponent:game.displayHome,displayAway:game.displayAway,displayHome:game.displayHome,location:game.displayAway===game.team?game.location:'Away'});
        const bet=row.querySelector('.bigsky-betting');
        const o=odds?.__allBooks?odds:(odds?.__multi?odds:(odds?.__circa?(circaFormatOdds(odds)||bigSkyFormatOdds(odds)):bigSkyFormatOdds(odds)));
        if(bet)bet.innerHTML=o?.html?`${o.html}<small>${escapeHtml(o.sub||'CURRENT MARKET LINES')}</small>`:`<b>LINE NOT POSTED</b><small>CHECK AGAIN LATER</small>`;
      }catch(e){const bet=row.querySelector('.bigsky-betting');if(bet)bet.innerHTML='<b>LINE NOT POSTED</b><small>CHECK AGAIN LATER</small>';}
    }));
  }
  function injectStyles(){
    if(document.getElementById('ghq-fcs-scoreboard-surgical-styles'))return;
    const s=document.createElement('style');s.id='ghq-fcs-scoreboard-surgical-styles';s.textContent=`
      .ghq-fcs-rank-card{overflow:hidden!important}.ghq-fcs-top-matchup{min-width:0!important}.ghq-fcs-rank-heading{display:flex!important;align-items:center!important;gap:10px!important;width:100%!important;min-height:30px!important}.ghq-fcs-rank-heading b{display:inline-block!important;visibility:visible!important;opacity:1!important;color:#151515!important;font-size:17px!important;font-weight:800!important;line-height:1.2!important;white-space:normal!important}.ghq-fcs-rank-heading strong{margin-left:auto!important;color:#151515!important}.ghq-fcs-scheduled{display:flex!important;gap:8px!important;align-items:center!important;margin:9px 0 4px!important;font-size:14px!important;color:#151515!important}.ghq-fcs-scheduled span{opacity:.55!important}.ghq-fcs-team-row{display:flex!important;align-items:center!important;min-width:0!important;gap:8px!important}.ghq-fcs-team-row span{display:block!important;visibility:visible!important;opacity:1!important;color:#151515!important;font-weight:700!important;white-space:normal!important}.ghq-fcs-team-row img{width:26px!important;height:26px!important;object-fit:contain!important;flex:0 0 26px!important}.ghq-fcs-team-row strong{margin-left:auto!important}.ghq-fcs-scheduled-teams{display:flex!important;align-items:center!important;gap:8px!important}.ghq-fcs-scheduled-teams .ghq-fcs-team-row{min-width:0!important;flex:1 1 0!important}.ghq-fcs-scheduled-teams .ghq-fcs-team-row span{font-size:13px!important}.ghq-fcs-game .bigsky-betting{min-width:180px!important}.ghq-fcs-game .fcs-matchup{min-width:0!important}
      .ghq-fcs-top-scorecard{display:flex!important;flex-direction:column!important;gap:0!important;padding:8px 10px!important;min-width:0!important}
      .ghq-fcs-top-team-row{display:grid!important;grid-template-columns:34px 30px minmax(0,1fr) auto!important;align-items:center!important;min-height:42px!important;gap:7px!important;border-bottom:1px solid #e6e6e6!important;color:#151515!important}
      .ghq-fcs-top-team-row:last-of-type{border-bottom:0!important}
      .ghq-fcs-top-team-row .fcs-team-rank{display:flex!important;align-items:center!important;justify-content:center!important;background:#8c1531!important;color:#fff!important;border-radius:5px!important;font-size:12px!important;font-weight:900!important;min-height:25px!important;padding:0 4px!important}
      .ghq-fcs-top-team-row .fcs-team-rank-empty{background:transparent!important}
      .ghq-fcs-top-team-row img{width:28px!important;height:28px!important;object-fit:contain!important;display:block!important}
      .ghq-fcs-top-logo-slot{width:30px!important;height:30px!important;display:flex!important;align-items:center!important;justify-content:center!important;min-width:30px!important}
      .ghq-fcs-top-team-row>span:not(.fcs-team-rank):not(.ghq-fcs-top-logo-slot){font-size:15px!important;font-weight:750!important;line-height:1.15!important;min-width:0!important;white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
      .ghq-fcs-top-team-row strong{font-size:18px!important;font-weight:900!important;margin-left:auto!important}
      .ghq-fcs-top-meta{display:flex!important;justify-content:flex-end!important;align-items:center!important;gap:8px!important;padding-top:6px!important;font-size:11px!important;color:#666!important;text-transform:uppercase!important;letter-spacing:.03em!important}
      .ghq-fcs-top-meta small{font-size:10px!important;color:#777!important}
      @media(max-width:700px){.ghq-fcs-top-team-row{grid-template-columns:31px 27px minmax(0,1fr) auto!important}.ghq-fcs-top-team-row img{width:25px!important;height:25px!important}.ghq-fcs-top-logo-slot{width:27px!important;height:27px!important;min-width:27px!important}.ghq-fcs-top-team-row>span:not(.fcs-team-rank):not(.ghq-fcs-top-logo-slot){font-size:14px!important}}

    `;document.head.appendChild(s);
  }
  injectStyles();

  async function draw(){
    const w=weeks[Number(weekEl.value)||0];
    if(statusEl)statusEl.textContent='Loading FCS scores…';
    const scheduled=scheduleGamesForWeek(w);
    const cached=cachedEventsForWeek(w);
    const rawLive=await fetchESPNEvents(w);
    const normalizedLive=rawLive.map(normalizeEvent);
    // Merge live and cached feeds instead of letting an incomplete live ESPN
    // response erase cached games. Live data wins when the same event exists.
    const eventMap=new Map();
    cached.forEach(e=>eventMap.set(String(e.id||JSON.stringify(e)),e));
    normalizedLive.forEach(e=>eventMap.set(String(e.id||JSON.stringify(e)),e));
    const eventPool=[...eventMap.values()];
    const merged=scheduled.map(g=>({g,ev:liveOrCachedForGame(g,normalizedLive,cached)}));

    const covered=new Set();
    scheduled.forEach(g=>{
      for(const team of [g.displayAway,g.displayHome]){
        const key=canonicalBigSky(team);
        if(key)covered.add(key);
      }
    });
    const uniqueBigSkyGames=scheduled.length;
    if(bigSkyLabelEl)bigSkyLabelEl.textContent=`${uniqueBigSkyGames} games • ${covered.size}/13 Big Sky teams scheduled`;
    if(statusEl)statusEl.textContent=`${uniqueBigSkyGames} Big Sky games • ${covered.size}/13 teams scheduled`;

    topEl.innerHTML=top25.slice(0,25).map(t=>top25Card(t,eventPool,scheduled)).join('')||'<div class="fcs-loading">Rankings unavailable.</div>';
    if(bigSkyEl)bigSkyEl.innerHTML=merged.map(x=>gameCard(x.g,x.ev)).join('')||'<div class="fcs-loading">No Big Sky games scheduled this week.</div>';
    await enrichScoreCards(scheduled,normalizedLive);
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
