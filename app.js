
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


function normalizeNewsImageUrl(url) {
  const value = String(url || '').trim();
  if (!value) return '';
  // GoGriz image-handler URLs can include a thumbnail preset that makes the
  // lead story look soft when it is enlarged in the homepage hero.
  if (/gogriz\.com\/common\/controls\/image_handler\.aspx/i.test(value)) {
    return value
      .replace(/([?&])thumb_prefix=[^&]*&?/i, '$1')
      .replace(/[?&]$/, '');
  }
  return value;
}

function renderHomepageNews(stories) {
  if (!Array.isArray(stories) || !stories.length) return;
  const clean = stories.filter(x => x && x.title && x.url);
  if (!clean.length) return;
  const featured = clean[0];
  const feature = document.querySelector('.espn-feature-card, .v2-feature');
  if (feature) {
    feature.href = featured.url;
    feature.target = '_blank';
    feature.rel = 'noopener';
    const image = feature.querySelector('img');
    const kicker = feature.querySelector('.espn-kicker, .v2-tag');
    const title = feature.querySelector('h2, h1');
    const description = feature.querySelector('p');
    const readMore = feature.querySelector('b, a.v2-button');
    if (image) {
      if (featured.image) image.src = normalizeNewsImageUrl(featured.image);
      image.alt = featured.title;
    }
    if (kicker) kicker.textContent = featured.source || featured.badge || 'LATEST';
    if (title) title.textContent = featured.title;
    if (description) description.textContent = featured.description || 'Latest Montana football news and coverage.';
    if (readMore) readMore.textContent = 'READ ARTICLE ↗';
  }
  const rows = document.querySelectorAll('#home-news-side .espn-news-row, #home-news-side .v2-story');
  clean.slice(1, 5).forEach((story, i) => {
    const row = rows[i];
    if (!row) return;
    row.href = story.url;
    row.target = '_blank';
    row.rel = 'noopener';
    const rowImage = row.querySelector('img');
    if (rowImage && story.image) { rowImage.src = story.image; rowImage.alt = story.title; }
    const source = row.querySelector('span');
    const title = row.querySelector('h3');
    const description = row.querySelector('p, small');
    if (source) source.textContent = story.source || story.badge || 'NEWS';
    if (title) title.textContent = story.title;
    if (description) description.textContent = story.description || story.date || '';
  });
}

async function loadHomepageNews() {
  try {
    const response = await fetch('news.json?ts=' + Date.now(), {cache: 'no-store'});
    if (!response.ok) return;
    const payload = await response.json();
    renderHomepageNews(payload.stories || payload.news || payload);
  } catch (error) {
    console.warn('Homepage news feed unavailable; using fallback content.', error);
  }
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
    applyRankingSnapshotFallback(d);
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
      applyRankingSnapshotFallback(d);
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
function applyRankingSnapshotFallback(data) {
  // Prefer the automatically refreshed data.json snapshot. The ESPN browser
  // endpoint can temporarily lag the official weekly poll; when that happens
  // never fall back all the way to the hard-coded preseason snapshot.
  const coachesRaw = Array.isArray(data?.coaches_poll) ? data.coaches_poll : [];
  const mediaRaw = Array.isArray(data?.media_poll) ? data.media_poll : [];
  const coaches = coachesRaw.length >= 25
    ? coachesRaw.map((name, i) => normalizeRankingEntry(name, i + 1))
    : RANKING_SNAPSHOTS.coaches.teams;
  const media = mediaRaw.length >= 25
    ? mediaRaw.map((name, i) => normalizeRankingEntry(name, i + 1))
    : RANKING_SNAPSHOTS.media.teams;
  renderPoll("coaches-poll", coaches);
  renderPoll("media-poll", media);
  window.__grizMediaPoll = media;
  renderMiniPolls(coaches, media);
  const rankDate = document.getElementById("rankings-date");
  if (rankDate) {
    const coachesDate = data?.rankings_date || RANKING_SNAPSHOTS.coaches.date;
    const mediaDate = data?.rankings_date || RANKING_SNAPSHOTS.media.date;
    rankDate.textContent = `Coaches • ${coachesDate} | Stats Perform • ${mediaDate}`;
  }
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
loadHomepageNews();
loadGrizData();

// Add the official Griz Gameday hub to the Next Up section without changing
// the existing matchup layout.
function addOfficialGamedayLink() {
  const quicklinks = document.querySelector('.ghq-nu-quicklinks');
  if (!quicklinks || quicklinks.querySelector('[data-official-gameday]')) return;
  const grid = quicklinks.querySelector('.ghq-nu-link-grid');
  if (!grid) return;
  const link = document.createElement('a');
  link.href = 'https://gogriz.com/gameday/football-vs-utah-tech/football/99/';
  link.target = '_blank';
  link.rel = 'noopener';
  link.dataset.officialGameday = 'true';
  link.innerHTML = '<strong>OFFICIAL GAMEDAY HUB</strong><span>Tickets, parking, promotions & more</span><em>↗</em>';
  grid.prepend(link);
}
addOfficialGamedayLink();
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

function renderBigSkyHub(d){
  const standingsEl=document.getElementById("bigsky-standings");
  const playersEl=document.getElementById("bigsky-players-of-week");
  const playersUpdatedEl=document.getElementById("bigsky-players-updated");
  const leadersEl=document.getElementById("bigsky-leaders");
  const newsEl=document.getElementById("bigsky-news");
  const rankedEl=document.getElementById("bigsky-ranked");
  const grizEl=document.getElementById("bigsky-griz-card");
  const updatedEl=document.getElementById("bigsky-standings-updated");
  const standings=Array.isArray(d.big_sky_standings)?d.big_sky_standings:[];
  const leaders=d.big_sky_leaders&&typeof d.big_sky_leaders==="object"?d.big_sky_leaders:{};
  const news=Array.isArray(d.big_sky_news)?d.big_sky_news:[];
  const players=Array.isArray(d.big_sky_players_of_week)?d.big_sky_players_of_week:[];
  const coaches=Array.isArray(d.coaches_poll)?d.coaches_poll:[];
  const statsPerform=Array.isArray(d.fcs_rankings)?d.fcs_rankings:[];
  if(updatedEl) updatedEl.textContent=standings.length ? "UPDATED "+new Date(d.big_sky_hub_updated||d.updated||Date.now()).toLocaleDateString("en-US",{month:"short",day:"numeric"}) : "DATA UNAVAILABLE";
  if(standingsEl){
    let out='<div class="bigsky-standing-row bigsky-standing-head"><span>#</span><span>TEAM</span><span>BIG SKY</span><span>OVERALL</span><span>PF-PA</span><span>STREAK</span></div>';
    if(standings.length){
      standings.forEach(function(t,i){
        const griz=t.team==="Montana";
        const logo=bigSkyLogo(t.team);
        out+='<div class="bigsky-standing-row '+(griz?"griz-row":"")+'"><span class="stand-rank">'+escapeHtml(t.rank||i+1)+'</span><span class="stand-team">'+(logo?'<img src="'+logo+'" alt="" loading="lazy">':"")+'<b>'+escapeHtml(t.team)+'</b></span><span>'+escapeHtml(t.conference_record||"—")+'</span><span>'+escapeHtml(t.overall_record||"—")+'</span><span>'+escapeHtml(t.points||"—")+'</span><span>'+escapeHtml(t.overall_streak||"—")+'</span></div>';
      });
    }else out='<div class="bigsky-empty">Standings are temporarily unavailable.</div>';
    standingsEl.innerHTML=out;
  }
  if(playersEl){
    if(playersUpdatedEl) playersUpdatedEl.textContent=players.length ? "WEEK "+escapeHtml(players[0].week||"") : "AWAITING WEEKLY HONORS";
    playersEl.innerHTML=players.length ? players.map(function(p){
      const category=String(p.category||"PLAYER OF THE WEEK");
      return '<article class="bigsky-pow-card"><div class="bigsky-pow-category">'+escapeHtml(category)+'</div><div class="bigsky-pow-player">'+escapeHtml(p.player||"—")+'</div><div class="bigsky-pow-school">'+escapeHtml(p.school||"")+(p.position?' • '+escapeHtml(p.position):"")+'</div><p>'+escapeHtml(p.summary||"")+'</p></article>';
    }).join("") : '<div class="bigsky-empty">Weekly honors are temporarily unavailable.</div>';
  }
  const leaderMeta={rushing:["RUSHING","YDS"],passing:["PASSING","YDS"],receiving:["RECEIVING","YDS"],tackles:["TACKLES","TOTAL"],sacks:["SACKS","TOTAL"],scoring:["SCORING","PTS"]};
  if(leadersEl){
    const keys=["rushing","passing","receiving","tackles","sacks","scoring"];
    leadersEl.innerHTML=keys.map(function(k){
      const arr=Array.isArray(leaders[k])?leaders[k].slice(0,5):[];
      const meta=leaderMeta[k];
      let body="";
      if(arr.length){
        body=arr.map(function(p,i){return '<div class="bigsky-leader-row"><span class="leader-num">'+(i+1)+'</span><div><strong>'+escapeHtml(p.name)+'</strong><small>'+escapeHtml(p.school)+'</small></div><b>'+escapeHtml(p.value||"—")+'</b></div>';}).join("");
      }else body='<div class="bigsky-empty">No current data.</div>';
      return '<div class="bigsky-leader-card"><div class="bigsky-leader-head"><b>'+meta[0]+'</b><span>'+meta[1]+'</span></div>'+body+'</div>';
    }).join("");
  }
  if(rankedEl){
    const ranked=[];
    const addRanked=function(list,poll){
      list.forEach(function(item,i){
        const rawName=typeof item==="string"?item:(item&&item.name)||"";
        const name=String(rawName).replace(/\s*\([^)]*\)\s*$/,"").trim();
        const rank=typeof item==="string"?i+1:(item&&item.rank)||i+1;
        const found=standings.some(function(s){return bigSkyNormTeam(s.team)===bigSkyNormTeam(name);});
        if(found && !ranked.some(function(x){return x.poll===poll && bigSkyNormTeam(x.name)===bigSkyNormTeam(name);})){ranked.push({name:name,rank:rank,poll:poll});}
      });
    };
    addRanked(coaches,"AFCA COACHES POLL");
    addRanked(statsPerform,"STATS PERFORM POLL");
    rankedEl.innerHTML=ranked.length?ranked.map(function(x){return '<div class="bigsky-ranked-row"><span>#'+x.rank+'</span><b>'+escapeHtml(x.name)+'</b><small>'+escapeHtml(x.poll)+'</small></div>';}).join(""):'<div class="bigsky-empty">No ranked Big Sky teams listed.</div>';
  }
  if(newsEl){
    newsEl.innerHTML=news.length?news.slice(0,6).map(function(n){return '<a class="bigsky-news-item" href="'+escapeHtml(n.url||"#")+'" target="_blank" rel="noopener"><small>'+escapeHtml(n.date||"BIG SKY FOOTBALL")+'</small><b>'+escapeHtml(n.title)+'</b><span>'+escapeHtml(n.description||"")+'</span></a>';}).join(""):'<div class="bigsky-empty">Conference news is temporarily unavailable.</div>';
  }
  if(grizEl){
    const griz=standings.find(function(x){return bigSkyTeamKey(x.team)==="montana";});
    const next=d.next_game||{};
    grizEl.innerHTML=griz?'<div class="bigsky-griz-record"><b>'+escapeHtml(griz.overall_record)+'</b><span>OVERALL</span><b>'+escapeHtml(griz.conference_record)+'</b><span>BIG SKY</span></div><div class="bigsky-griz-next"><small>NEXT GAME</small><strong>'+escapeHtml(next.opponent||"—")+'</strong><span>'+escapeHtml([next.date,next.time].filter(Boolean).join(" • ")||"Schedule pending")+'</span></div>':'<div class="bigsky-empty">Montana standings unavailable.</div>';
  }
}
(async function loadBigSkyHub(){
  try{
    const r=await fetch("data.json?ts="+Date.now(),{cache:"no-store"});
    const d=await r.json();
    renderBigSkyHub(d);
  }catch(e){console.warn("Big Sky hub data unavailable",e);}
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
    await loadHomepageNews();
loadGrizData();
    await renderBigSkyAndOpponent();
  } catch (e) {
    console.warn("Automatic Griz HQ refresh failed", e);
  }
}, 60 * 1000);


/* AUTHORITATIVE NEXT-GAME CONTROLLER — FULL OPPONENT DOSSIER
   The matchup shell AND the entire Next Up dossier are driven from the first
   Montana schedule entry without a final result. The HTML contains a layout
   only; opponent-specific copy is supplied here so last week's opponent can
   never remain after the schedule advances. */
(function installAuthoritativeNextGameController(){
  const NEXT_GAME_LOGOS = {
    "Southern Utah":"https://a.espncdn.com/i/teamlogos/ncaa/500/253.png",
    "Drake":"https://a.espncdn.com/i/teamlogos/ncaa/500/2181.png",
    "Utah Tech":"https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png",
    "Oregon State":"https://a.espncdn.com/i/teamlogos/ncaa/500/204.png",
    "UC Davis":"https://a.espncdn.com/i/teamlogos/ncaa/500/302.png",
    "Northern Colorado":"https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png",
    "Northern Arizona":"https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png",
    "Idaho":"https://a.espncdn.com/i/teamlogos/ncaa/500/70.png",
    "Eastern Washington":"https://a.espncdn.com/i/teamlogos/ncaa/500/331.png",
    "Portland State":"https://a.espncdn.com/i/teamlogos/ncaa/500/279.png",
    "Idaho State":"https://a.espncdn.com/i/teamlogos/ncaa/500/304.png",
    "Montana State":"https://a.espncdn.com/i/teamlogos/ncaa/500/147.png"
  };
  const NEXT_GAME_VENUES = {
    "Oregon State":"Reser Stadium, Corvallis, Ore.",
    "UC Davis":"UC Davis Health Stadium, Davis, Calif.",
    "Northern Arizona":"J. Lawrence Walkup Skydome, Flagstaff, Ariz.",
    "Eastern Washington":"Roos Field, Cheney, Wash.",
    "Montana State":"Bobcat Stadium, Bozeman, Mont.",
    "Portland State":"Hillsboro Stadium, Hillsboro, Ore.",
    "Idaho State":"Davis Wade Stadium, Pocatello, Idaho",
    "Idaho":"Washington-Grizzly Stadium, Missoula, Mont.",
    "Northern Colorado":"Washington-Grizzly Stadium, Missoula, Mont.",
    "Southern Utah":"Washington-Grizzly Stadium, Missoula, Mont.",
    "Utah Tech":"Washington-Grizzly Stadium, Missoula, Mont."
  };
  const OFFICIAL_ROOTS = {
    "Oregon State":"https://osubeavers.com/sports/football",
    "UC Davis":"https://ucdavisaggies.com/sports/football",
    "Northern Colorado":"https://uncbears.com/sports/football",
    "Northern Arizona":"https://nauathletics.com/sports/football",
    "Idaho":"https://govandals.com/sports/football",
    "Eastern Washington":"https://goeags.com/sports/football",
    "Portland State":"https://goviks.com/sports/football",
    "Idaho State":"https://isubengals.com/sports/football",
    "Montana State":"https://msubobcats.com/sports/football",
    "Southern Utah":"https://suutbirds.com/sports/football",
    "Utah Tech":"https://utahtechtrailblazers.com/sports/football",
    "Drake":"https://godrakebulldogs.com/sports/football"
  };
  const PROFILES = {
    "Oregon State": {
      record:"0–2", conferenceRecord:"0–0", location:"Corvallis, Ore.", capacity:"35,548",
      coach:"JaMarcus Shephard", coachLine:"First season as Oregon State head coach",
      stats:{points:"22.0", offense:"437.0", passing:"396.5", rushing:"40.5", allowed:"34.0", defense:"442.5", third:"26.7%", turnovers:"+2"},
      recent:[
        ["Oregon State","L","20–33","Houston"],["","L","24–35","Texas Tech"]
      ],
      players:[
        ["OS","Braden Atkinson","Oregon State QB • 789 passing yards • 3 TD"],
        ["OS","Jesse Legree","Oregon State WR • 376 receiving yards • 3 TD"],
        ["OS","Kourdey Glass","Oregon State RB • 25 rushing yards"],
        ["OS","Takari Hickle","Oregon State EDGE • TFL in six straight games entering Montana"],
      ],
      intel:"Oregon State enters Game 3 at 0–2 after losses to Houston and Texas Tech. Saturday is the Beavers' third game of the 2026 season and their first meeting with Montana since 1996. The program is in its first season under head coach JaMarcus Shephard.",
      facts:[["0–2","Current record"],["2026","First season under Shephard"],["35,548","Reser Stadium capacity"],["Corvallis","Home of the Beavers"]],
      historyTitle:"THE BEAVERS LEAD THE ALL-TIME SERIES",
      historyText:"Oregon State leads the all-time series 12–2–2. The teams have not met since 1996, when Montana won 35–14 in Corvallis. Montana has won the last two meetings.",
      historyGames:[["1996","MONTANA 35–14","Corvallis"],["1990","MONTANA 22–15","Missoula"],["2026","NEXT CHAPTER","Reser Stadium"]],
      watch:[
        ["Can Montana handle Oregon State's passing volume?","The Beavers have 793 passing yards through two games and are averaging 396.5 passing yards per game."],
        ["Can the Griz limit Jesse Legree?","The freshman leads Oregon State with 376 receiving yards and has produced a 70-plus-yard catch in each game."],
        ["Can Montana win the run game?","Oregon State is averaging 40.5 rushing yards per game through two contests."],
      ],
      checklist:[
        ["Quarterback tendencies","Track Braden Atkinson on early downs, pressure looks and explosive throws."],
        ["Explosive passes","Legree already has 71- and 75-yard receptions this season."],
        ["Run defense","Oregon State has gained 81 rushing yards through two games."],
        ["Third down","The Beavers are converting 26.7% of third downs through two games."],
      ],
      moreNumbers:[["PASSING","396.5","Oregon State passing yards per game"],["TOTAL OFFENSE","437.0","Total yards per game"],["RUSHING","40.5","Rushing yards per game"],["POINTS","22.0","Points per game"],["POINTS ALLOWED","34.0","Opponent points per game"],["3RD DOWN","26.7%","Third-down conversion rate"]],
      media:[
        ["HIGHLIGHTS","Search Oregon State 2026 Highlights","Recent game clips and team highlights","https://www.youtube.com/results?search_query=Oregon+State+football+2026+highlights"],
        ["COACH TALK","JaMarcus Shephard Press Conferences","Hear the opponent's coaches directly","https://www.youtube.com/results?search_query=JaMarcus+Shephard+Oregon+State+2026+press+conference"],
        ["RECENT GAME","Oregon State vs. Texas Tech","Full-game, recap and highlight video","https://www.youtube.com/results?search_query=Oregon+State+Texas+Tech+2026+football"],
        ["RECENT GAME","Oregon State at Houston","Another look at the Beavers' season opener","https://www.youtube.com/results?search_query=Oregon+State+Houston+2026+football"]
      ]
    }
  };
  function finished(game){ return !!String(game && game.result || '').trim(); }
  function chooseNext(data){
    const schedule=Array.isArray(data && data.schedule) ? data.schedule : [];
    return schedule.find(g=>g && g.opponent && !finished(g)) || data.next_game || {};
  }
  function esc(v){
    return String(v == null ? "" : v).replace(/[&<>\"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  }
  function text(el,value){ if(el && value!=null) el.textContent=String(value); }
  function attr(el,name,value){ if(el && value) el.setAttribute(name,value); }
  function rootFor(opponent){ return OFFICIAL_ROOTS[opponent] || `https://www.google.com/search?q=${encodeURIComponent(opponent+" football")}`; }
  function link(root,path){ return path ? root.replace(/\/$/,"")+path : root; }
  function montanaRecord(schedule){
    const played=(schedule||[]).filter(finished);
    const w=played.filter(g=>/^W/i.test(g.result)).length;
    const l=played.filter(g=>/^L/i.test(g.result)).length;
    const conf=played.filter(g=>g.conference);
    return {record:`${w}–${l}`, conference:`${conf.filter(g=>/^W/i.test(g.result)).length}–${conf.filter(g=>/^L/i.test(g.result)).length}`};
  }
  function montanaRecent(schedule){
    return (schedule||[]).filter(finished).slice(-2).reverse().map((g,i)=>[i?"": "MONTANA", /^W/i.test(g.result)?"W":"L", String(g.result).replace(/^[WL]\s*/i,""), g.opponent]);
  }
  function profileFor(opponent){ return PROFILES[opponent] || null; }
  function resourceSet(opponent,data){
    const root=rootFor(opponent);
    const existing=(data && data.opponent_resources && data.opponent_resources[opponent]) || {};
    return {
      official:existing.official || root,
      roster:existing.roster || link(root,"/roster"),
      stats:existing.stats || link(root,"/stats/2026"),
      schedule:existing.schedule || link(root,"/schedule/2026"),
      coaches:existing.coaches || link(root,"/coaches"),
      news:existing.news || link(root,"/news")
    };
  }
  function renderQuickLinks(section, opponent, resources){
    const grid=section.querySelector('.ghq-nu-link-grid'); if(!grid) return;
    const items=[
      ["OFFICIAL FOOTBALL","Official team home",resources.official],
      ["ROSTER","Players & bios",resources.roster],
      ["2026 STATS","Team & player stats",resources.stats],
      ["SCHEDULE","Full 2026 slate",resources.schedule],
      ["COACHES","Staff & leadership",resources.coaches],
      ["TEAM NEWS","Latest opponent coverage",resources.news],
      ["OPPONENT HISTORY","Montana vs. "+opponent,resources.official],
      ["GRIZ GAME CENTER","Live stats & game info","https://gogriz.com/sports/football"]
    ];
    grid.innerHTML=items.map(x=>`<a href="${esc(x[2])}" target="_blank" rel="noopener"><strong>${esc(x[0])}</strong><span>${esc(x[1])}</span><em>↗</em></a>`).join('');
  }
  function renderStats(section, profile, mr){
    const head=section.querySelector('.ghq-nu-compare-head');
    if(head){
      const bs=head.querySelectorAll('b'); if(bs[0]) text(bs[0],`MONTANA`); if(bs[1]) text(bs[1],profile?section.dataset.opponent.toUpperCase():section.dataset.opponent.toUpperCase());
    }
    const mtStats={record:mr.record,points:section.dataset.mtPpg||'—',offense:section.dataset.mtOffense||'—',passing:section.dataset.mtPassing||'—',rushing:section.dataset.mtRushing||'—',allowed:section.dataset.mtAllowed||'—',defense:section.dataset.mtDefense||'—',third:section.dataset.mtThird||'—',turnovers:section.dataset.mtTurnovers||'—'};
    const vals=section.querySelectorAll('.ghq-nu-stat');
    const keys=['record','points','offense','passing','rushing','allowed','defense','third','turnovers'];
    vals.forEach((row,i)=>{
      const strong=row.querySelectorAll('strong');
      if(strong[0]) text(strong[0],mtStats[keys[i]]||'—');
      if(strong[1]) text(strong[1],profile ? (profile.stats[keys[i]]||'—') : '—');
      strong.forEach(x=>x.classList.remove('better'));
    });
  }
  function renderPlayers(section, profile, data){
    const cards=section.querySelectorAll('.ghq-nu-player');
    const mtLeaders=data?.stats?.leaders || {};
    const mt=[
      ["M","Eli Gillman",mtLeaders.rushing?.[0]?.line ? `Montana RB • ${mtLeaders.rushing[0].line.replaceAll('•','•')}` : "Montana RB"],
      ["M","Keali'i Ah Yat",mtLeaders.passing?.[0]?.line ? `Montana QB • ${mtLeaders.passing[0].line}` : "Montana QB"],
    ];
    const opp=profile?.players || [["OP",profile ? `${section.dataset.opponent} leaders` : "Opponent leaders","Opponent-specific player data will populate when available"],["OP","Key player","See official roster and stats"]];
    const all=mt.concat(opp).slice(0,4);
    cards.forEach((card,i)=>{ const x=all[i]; if(!x) return; text(card.querySelector('.ghq-nu-player-team'),x[0]); text(card.querySelector('b'),x[1]); text(card.querySelector('span'),x[2]); card.querySelector('.ghq-nu-player-team')?.classList.toggle('opp',i>=2); card.querySelector('.ghq-nu-player-team')?.classList.toggle('griz',i<2); });
  }
  function renderHistory(section, profile, opponent){
    const copy=section.querySelector('.ghq-nu-history-copy');
    const games=section.querySelector('.ghq-nu-history-games');
    if(!profile){
      text(copy?.querySelector('h2'),`MONTANA VS. ${opponent.toUpperCase()}`);
      text(copy?.querySelector('p'),`Series history for Montana and ${opponent} is kept current from the official records. Detailed historical results can be added without changing the automatic opponent switch.`);
      const score=copy?.querySelector('.ghq-nu-series-score');
      if(score){ Array.from(score.children).forEach((box,i)=>{ text(box.querySelector('b'),i===2?'NEXT':'—'); text(box.querySelector('span'),i===2?'Upcoming chapter':'Series history'); }); }
      if(games){ games.innerHTML=`<div><span>HISTORY</span><b>MONTANA VS. ${esc(opponent.toUpperCase())}</b><small>Official series records</small></div><div class="next-series"><span>NEXT</span><b>UPCOMING</b><small>${esc(section.dataset.venue||'Next game')}</small></div>`; }
      return;
    }
    text(copy?.querySelector('h2'),profile.historyTitle);
    text(copy?.querySelector('p'),profile.historyText);
    const score=copy?.querySelector('.ghq-nu-series-score');
    if(score){ const vals=profile.historyGames; text(score.children[0]?.querySelector('b'),profile.record==='0–2'?'12–2–2':'—'); text(score.children[0]?.querySelector('span'),'Oregon State all-time'); text(score.children[1]?.querySelector('b'),'Last meeting: 1996'); text(score.children[1]?.querySelector('span'),'35–14 Montana'); text(score.children[2]?.querySelector('b'),'1996'); text(score.children[2]?.querySelector('span'),'Last meeting'); }
    if(games){ games.innerHTML=profile.historyGames.map((g,i)=>`<div${i===2?' class="next-series"':''}><span>${esc(g[0])}</span><b>${esc(g[1])}</b><small>${esc(g[2])}</small></div>`).join(''); }
  }
  function renderWatch(section, profile, opponent){
    const lists=section.querySelectorAll('.ghq-nu-watchlist');
    const w=profile?.watch || [[`What should Montana watch against ${opponent}?`,`Track the opponent's quarterback, explosive plays, third-down approach and special teams.`],[`Where can the game turn?`,`Use the opponent's latest official stats and game film to identify the biggest matchup points.`],[`What changed this week?`,`Check the opponent's latest news and press conferences before kickoff.`]];
    const c=profile?.checklist || [["Quarterback tendencies",`Study ${opponent}'s early-down throws and pressure response.`],["Explosive plays",`Identify the opponent's longest runs, passes and returns.`],["Third-down defense",`Track third-down personnel, pressures and conversion rate.`],["Special teams",`Review punt, kickoff, field-goal and fake-punt tendencies.`]];
    if(lists[0]) lists[0].innerHTML=w.map((x,i)=>`<li><b>${esc(x[0])}</b><span>${esc(x[1])}</span></li>`).join('');
    if(lists[1]) lists[1].innerHTML=c.map(x=>`<li><b>${esc(x[0])}</b><span>${esc(x[1])}</span></li>`).join('');
  }
  function renderMedia(section, profile, opponent){
    const cards=section.querySelectorAll('.ghq-nu-media-card');
    const media=profile?.media || [
      ["HIGHLIGHTS",`Search ${opponent} 2026 Highlights`,`Recent game clips and team highlights`,`https://www.youtube.com/results?search_query=${encodeURIComponent(opponent+' football 2026 highlights')}`],
      ["COACH TALK",`${opponent} Press Conferences`,`Hear the opponent's coaches directly`,`https://www.youtube.com/results?search_query=${encodeURIComponent(opponent+' football 2026 press conference')}`],
      ["RECENT GAME",`${opponent} Recent Game`,`Full-game, recap and highlight video`,`https://www.youtube.com/results?search_query=${encodeURIComponent(opponent+' football 2026 recent game')}`],
      ["NEWS",`${opponent} Football News`,`Latest opponent coverage`,`https://www.google.com/search?q=${encodeURIComponent(opponent+' football news')}`]
    ];
    cards.forEach((card,i)=>{ const x=media[i]; if(!x) return; card.href=x[3]; text(card.querySelector('span'),x[0]); text(card.querySelector('b'),x[1]); text(card.querySelector('small'),x[2]); });
  }
  function renderResearch(section, opponent, resources){
    const grid=section.querySelector('.ghq-nu-research-grid'); if(!grid) return;
    const items=[["TEAM STATS","Offense, defense & special teams",resources.stats],["ROSTER & BIOS","Every player and position",resources.roster],["COACHING STAFF","Head coach & coordinators",resources.coaches],["TEAM NEWS","Latest opponent coverage",resources.news],["FULL SCHEDULE","Results & upcoming games",resources.schedule],["SERIES HISTORY","Montana vs. "+opponent,"https://gogriz.com/sports/football"]];
    grid.innerHTML=items.map(x=>`<a href="${esc(x[2])}" target="_blank" rel="noopener"><b>${esc(x[0])}</b><span>${esc(x[1])}</span></a>`).join('');
  }
  function renderMoreNumbers(section, profile, opponent){
    const cards=section.querySelectorAll('.ghq-nu-stat-cards > div');
    const vals=profile?.moreNumbers || [["STATUS","UPDATING","Opponent-specific stats will appear here"],["ROSTER","OFFICIAL","Use the opponent roster for current players"],["SCHEDULE","CURRENT","Latest official schedule"],["FILM","AVAILABLE","Recent game video and pressers"],["NEWS","LIVE","Latest opponent coverage"],["RESEARCH","OPEN","Official stats and roster"]];
    cards.forEach((card,i)=>{const x=vals[i]; if(!x) return; text(card.querySelector('span'),x[0]); text(card.querySelector('b'),x[1]); text(card.querySelector('small'),x[2]);});
  }
  function renderHomeNextGame(data, game){
  const section=document.querySelector('.v2-home-next'); if(!section || !game || !game.opponent) return;
  const schedule=Array.isArray(data?.schedule)?data.schedule:[];
  const mr=montanaRecord(schedule);
  const opponent=String(game.opponent);
  const location=String(game.location||'').toLowerCase();
  const away=location.includes('away') || location.includes('at ');
  const venue=GRIZ_GAME_VENUES[opponent]?.venue || (game.venue && game.venue!=='Away' ? game.venue : (away ? 'Away at '+opponent : 'Washington-Grizzly Stadium, Missoula, MT'));
  const matchup=section.querySelector('.v2-home-next-match');
  if(matchup){
    const cols=matchup.children;
    if(cols[0]){ text(cols[0].querySelector('strong'),'GRIZ'); const s=cols[0].querySelector('small'); if(s) s.innerHTML='MONTANA<br>'+esc(mr.record); }
    if(cols[1]){ const b=cols[1].querySelector('b'); if(b) b.innerHTML=esc(game.date||'')+'<br>'+esc(game.time||''); const s=cols[1].querySelector('small'); if(s) s.textContent=String(game.tv||game.stream||'ESPN+'); }
    if(cols[2]){ text(cols[2].querySelector('strong'),opponent.toUpperCase()); const s=cols[2].querySelector('small'); if(s) s.innerHTML=esc(opponent.toUpperCase())+'<br>UP NEXT'; }
  }
  const p=section.querySelector(':scope > p'); if(p) text(p,venue);
}
function renderHomeSnapshot(data){
  const section=document.querySelector('.v2-snapshot'); if(!section) return;
  const schedule=Array.isArray(data?.schedule)?data.schedule:[];
  const mr=montanaRecord(schedule);
  const poll=Array.isArray(data?.coaches_poll)?data.coaches_poll:[];
  const rankIndex=poll.findIndex(x=>/montana/i.test(String(x)));
  const rank=rankIndex>=0 ? '#'+(rankIndex+1) : '—';
  const grid=section.querySelector('.v2-snapshot-grid'); if(!grid) return;
  const cells=grid.children;
  if(cells[0]) text(cells[0].querySelector('b'),mr.record);
  if(cells[1]) text(cells[1].querySelector('b'),rank);
  if(cells[2]) text(cells[2].querySelector('b'),mr.conference);
}
function renderDossier(data){
    const game=chooseNext(data); if(!game || !game.opponent) return;
    const opponent=String(game.opponent), upper=opponent.toUpperCase(), profile=profileFor(opponent), resources=resourceSet(opponent,data); renderHomeNextGame(data,game); renderHomeSnapshot(data);
    const schedule=Array.isArray(data.schedule)?data.schedule:[], mr=montanaRecord(schedule);
    const nextSection=document.getElementById('next-up'); if(!nextSection) return;
    nextSection.dataset.nextOpponent=opponent; nextSection.dataset.opponent=opponent;
    const location=String(game.location||'').toLowerCase();
    const away=location.includes('away') || location.includes('at ');
    const venue=NEXT_GAME_VENUES[opponent] || (game.venue && game.venue!=='Away' ? game.venue : (away ? `Away at ${opponent}` : 'Washington-Grizzly Stadium, Missoula, Mont.'));
    const logo=NEXT_GAME_LOGOS[opponent]||'';
    text(nextSection.querySelector('.ghq-nu-hero h1 span'),upper);
    text(nextSection.querySelector('.ghq-nu-game-pill b'),String(game.date||'').toUpperCase());
    text(nextSection.querySelector('.ghq-nu-game-pill span'),String(game.time||'').toUpperCase());
    text(nextSection.querySelector('.ghq-nu-game-pill small'),venue.split(',')[0].toUpperCase());
    const teams=nextSection.querySelectorAll('.ghq-nu-team');
    if(teams[0]) text(teams[0].querySelector('p'),`${mr.record} • ${mr.conference} BIG SKY`);
    if(teams[1]){ text(teams[1].querySelector('h2'),upper); text(teams[1].querySelector('p'),profile?.record || 'UPCOMING'); attr(teams[1].querySelector('img'),'src',logo); attr(teams[1].querySelector('img'),'alt',`${opponent} logo`); }
    const sections=nextSection.querySelectorAll('.ghq-nu-section-head');
    if(sections[0]){ text(sections[0].querySelector('h2'),`MONTANA VS. ${upper}`); text(sections[0].querySelector('p'),profile ? `Through ${profile.record==='0–2'?'two':'the latest'} games for ${opponent}. Montana enters ${mr.record}.` : `Opponent dossier for ${opponent}. Montana enters ${mr.record}.`); }
    if(sections[1]){ text(sections[1].querySelector('h2'),`WATCH THE ${upper}`); text(sections[1].querySelector('p'),`Start the week with the video that matters: coach interviews, player press conferences, highlights and recent games involving ${opponent}.`); }
    if(sections[2]){ text(sections[2].querySelector('h2'),'STATS WORTH DIGGING INTO'); text(sections[2].querySelector('p'),`The scoreboard tells you who won. These numbers tell you how ${opponent} is built.`); }
    const quick=nextSection.querySelector('.ghq-nu-quicklinks'); renderQuickLinks(quick,opponent,resources);
    const teamSummary=Array.isArray(data?.stats?.team_summary)?data.stats.team_summary:[];
    const sum=k=>teamSummary.find(x=>x.label===k)?.value||'';
    nextSection.dataset.mtPpg=sum('POINTS / GAME')||'36.0';
    nextSection.dataset.mtOffense=sum('TOTAL OFFENSE')||'429.3';
    nextSection.dataset.mtPassing='264.3';
    nextSection.dataset.mtRushing='165.0';
    nextSection.dataset.mtAllowed=sum('POINTS ALLOWED')||'15.0';
    nextSection.dataset.mtDefense=sum('TOTAL DEFENSE')||'404.0';
    nextSection.dataset.mtThird='39.5%';
    nextSection.dataset.mtTurnovers='+3';
    renderStats(nextSection,profile,mr);
    const cols=nextSection.querySelectorAll('.ghq-nu-two-col');
    if(cols[0]){
      const edge=cols[0].querySelector('.ghq-nu-edge');
      if(edge){
        const mtP=Number(nextSection.dataset.mtPpg), oppP=Number(profile?.stats?.points), mtO=Number(nextSection.dataset.mtOffense), oppO=Number(profile?.stats?.offense), mtD=Number(nextSection.dataset.mtAllowed), oppD=Number(profile?.stats?.allowed);
        const diff=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)?`${(a-b>=0?'+':'')+(a-b).toFixed(1)}`:'—';
        const vals=profile ? [['SCORING',diff(mtP,oppP),'points/game difference'],['TOTAL OFFENSE',diff(mtO,oppO),'yards/game difference'],['RUSHING',diff(Number(nextSection.dataset.mtRushing),Number(profile.stats.rushing)),'yards/game difference'],['POINTS ALLOWED',diff(mtD,oppD),'points/game difference']] : [['SCORING','—',`Opponent scoring data not loaded for ${opponent}`],['TOTAL OFFENSE','—',`Opponent offense data not loaded for ${opponent}`],['RUSHING','—',`Opponent rushing data not loaded for ${opponent}`],['POINTS ALLOWED','—',`Opponent defensive data not loaded for ${opponent}`]];
        edge.querySelectorAll('div').forEach((d,i)=>{const x=vals[i]; if(!x)return; text(d.querySelector('span'),x[0]); text(d.querySelector('b'),x[1]); text(d.querySelector('small'),x[2]);});
      }
      const recent=cols[0].querySelector('.ghq-nu-card:nth-child(2)'); if(recent){
        const rows=recent.querySelectorAll('.ghq-nu-game-row'); const mt=montanaRecent(schedule), opp=profile?.recent || [[opponent,'','—','No completed games available'],['','', '—','Check official opponent schedule']];
        const all=mt.concat(opp).slice(0,4); rows.forEach((r,i)=>{const x=all[i];if(!x)return;text(r.querySelector('b'),x[0]);text(r.querySelector('span'),x[1]);text(r.querySelector('strong'),x[2]);text(r.querySelector('small'),x[3]);r.querySelector('span')?.classList.toggle('w',x[1]==='W');r.querySelector('span')?.classList.toggle('l',x[1]==='L');});
      }
    }
    if(cols[1]){
      renderPlayers(cols[1],profile,data);
      const intel=cols[1].querySelector('.ghq-nu-card:nth-child(2)');
      if(intel){ text(intel.querySelector('h3'),`GET TO KNOW THE ${upper}`); text(intel.querySelector('p'),profile?.intel || `${opponent} is Montana's next opponent. This dossier updates automatically from the next unplayed game on the Montana schedule.`); const facts=intel.querySelector('.ghq-nu-facts'); if(facts){const arr=profile?.facts || [["UPCOMING","Next opponent"],["—","Current record"],["OFFICIAL","Roster & stats"],[venue.split(',')[0],"Game venue"]]; facts.innerHTML=arr.map(x=>`<div><b>${esc(x[0])}</b><span>${esc(x[1])}</span></div>`).join('');}}
    }
    const history=nextSection.querySelector('.ghq-nu-history'); if(history) history.dataset.venue=venue; renderHistory(history,profile,opponent);
    const lists=nextSection.querySelectorAll('.ghq-nu-two-col');
    if(lists[2]) renderWatch(lists[2],profile,opponent);
    renderMedia(nextSection,profile,opponent);
    const research=nextSection.querySelector('.ghq-nu-research-grid')?.closest('.ghq-nu-card')?.parentElement;
    if(research) renderResearch(research,opponent,resources);
    renderMoreNumbers(nextSection,profile,opponent);
    const linkDump=nextSection.querySelector('.ghq-nu-link-dump .ghq-nu-resource-grid');
    if(linkDump){ linkDump.innerHTML=[["OFFICIAL FOOTBALL","Official athletics home",resources.official],["WEB NEWS","Latest web coverage",`https://www.google.com/search?q=${encodeURIComponent(opponent+' football news')}`],["YOUTUBE","Videos & pressers",`https://www.youtube.com/results?search_query=${encodeURIComponent(opponent+' football 2026')}`],["ESPN","Scores, roster & stats",opponent==='Oregon State' ? 'https://www.espn.com/college-football/team/_/id/204/oregon-state-beavers' : `https://www.google.com/search?q=${encodeURIComponent(opponent+' ESPN football')}`],["SCHEDULE","Game-by-game results",resources.schedule],["PODCASTS","Opponent discussion",`https://www.google.com/search?q=${encodeURIComponent(opponent+' football podcast')}`]].map(x=>`<a href="${esc(x[2])}" target="_blank" rel="noopener"><b>${esc(x[0])}</b><span>${esc(x[1])}</span></a>`).join(''); }
    const footer=nextSection.querySelector('.ghq-nu-footer'); if(footer){text(footer.querySelector('span:first-child'),`DATA SNAPSHOT • ${new Date().toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'})}`);text(footer.querySelector('span:last-child'),profile?`${opponent} statistics: official athletics • Montana statistics: Griz HQ`:`${opponent} information: official athletics • Montana information: Griz HQ`);}
  }
  async function refreshAuthoritativeNextGame(){
    try{ const r=await fetch('data.json?next-game-controller='+Date.now(),{cache:'no-store'}); if(!r.ok) return; renderDossier(await r.json()); }
    catch(e){ console.warn('Authoritative next-game refresh failed',e); }
  }
  refreshAuthoritativeNextGame();
  setInterval(refreshAuthoritativeNextGame,60000);
})();
