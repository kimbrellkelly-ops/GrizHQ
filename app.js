
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
  "Montana State": "https://a.espncdn.com/i/teamlogos/ncaa/500/147.png"
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
  "Utah Tech": {lat:37.1059, lon:-113.5667, venue:"Greater Zion Stadium"}
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

async function fetchBigSkyOdds(game){
  const [kalshi,multi,maddux,circa]=await Promise.all([
    fetchKalshiOdds(game),fetchWagerTalkOdds(game),fetchMadduxOdds(game),fetchCircaOdds(game)
  ]);
  const combined=formatAllBookLines(kalshi,multi,maddux,circa);
  if(combined)return {__allBooks:true,...combined};

  // Final fallback: ESPN game odds so the card does not go blank.
  const iso=bigSkyDateISO(game.date); if(!iso)return null;
  const cacheKey=iso;
  if(!BIG_SKY_ODDS_CACHE.has(cacheKey)){
    BIG_SKY_ODDS_CACHE.set(cacheKey,(async()=>{try{const ymd=iso.replaceAll('-','');const res=await fetch(`https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${ymd}&limit=500`,{cache:'no-store'});if(!res.ok)return [];const d=await res.json();return Array.isArray(d.events)?d.events:[];}catch(e){return [];}})());
  }
  const events=await BIG_SKY_ODDS_CACHE.get(cacheKey); const ev=events.find(e=>bigSkyEventMatches(e,game)); if(!ev)return null;
  const competition=ev.competitions?.[0]; let odds=Array.isArray(competition?.odds)?competition.odds[0]:competition?.odds;
  if(!odds&&ev.id){try{const r=await fetch(`https://cdn.espn.com/core/college-football/game?xhr=1&gameId=${ev.id}`,{cache:'no-store'});if(r.ok){const pkg=await r.json();const c=pkg?.gamepackageJSON?.header?.competitions?.[0]||pkg?.header?.competitions?.[0];odds=Array.isArray(c?.odds)?c.odds[0]:c?.odds;}}catch(e){}}
  return odds||null;
}

function bigSkyWeatherLabel(code){
  const map={0:'Clear',1:'Mostly clear',2:'Partly cloudy',3:'Overcast',45:'Fog',48:'Rime fog',51:'Light drizzle',53:'Drizzle',55:'Heavy drizzle',61:'Light rain',63:'Rain',65:'Heavy rain',71:'Light snow',73:'Snow',75:'Heavy snow',80:'Rain showers',81:'Rain showers',82:'Heavy showers',85:'Snow showers',86:'Heavy snow showers',95:'Thunderstorms',96:'T-storms + hail',99:'T-storms + hail'};
  return map[Number(code)] || 'Forecast';
}
async function fetchBigSkyWeather(game){
  const iso=bigSkyDateISO(game.date); const v=bigSkyVenueFor(game); if(!iso||!v) return null;
  const key=`${iso}|${v.lat}|${v.lon}`;
  if(!BIG_SKY_WEATHER_CACHE.has(key)){
    BIG_SKY_WEATHER_CACHE.set(key,(async()=>{
      try{
        const url=`https://api.open-meteo.com/v1/forecast?latitude=${v.lat}&longitude=${v.lon}&daily=weather_code,temperature_2m_max,precipitation_probability_max,wind_speed_10m_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&start_date=${iso}&end_date=${iso}`;
        const res=await fetch(url); const d=await res.json();
        if(!d.daily?.time?.length) return null;
        return {temp:d.daily.temperature_2m_max?.[0], code:d.daily.weather_code?.[0], rain:d.daily.precipitation_probability_max?.[0], wind:d.daily.wind_speed_10m_max?.[0], venue:v.venue};
      }catch(e){ return null; }
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
      if(weather){
        const temp=weather.temp!=null?`${Math.round(weather.temp)}°`:'TBD';
        const rain=weather.rain!=null?`${Math.round(weather.rain)}% rain`:'';
        const wind=weather.wind!=null?`${Math.round(weather.wind)} mph wind`:'';
        wx.innerHTML=`<b>${escapeHtml(temp)} • ${escapeHtml(bigSkyWeatherLabel(weather.code))}</b><small>${escapeHtml([rain,wind].filter(Boolean).join(' • ')||'Forecast')}</small>`;
      }else wx.innerHTML='<b>FORECAST TBD</b><small>GAME WEATHER</small>';
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
  'Southern Utah':'https://a.espncdn.com/i/teamlogos/ncaa/500/253.png'
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
        const team=x?.team||x||{};
        const name=team?.shortDisplayName||team?.displayName||team?.name||x?.short||x?.name||'Team';
        const logo=teamLogo(x);
        const rankForTeamForRow=(teamObj)=>{
          const rowName=teamObj?.displayName||teamObj?.shortDisplayName||teamObj?.name||teamObj?.abbreviation||'';
          const rowId=teamObj?.id ? String(teamObj.id) : '';
          const rowNorm=norm(rowName);
          for(const item of top25.slice(0,25)){
            const rankValue=String(item?.rank??'').trim();
            if(!rankValue) continue;
            const rankName=String(item?.team||'');
            const rankNorm=norm(rankName);
            // Prefer an explicit ID match when the rankings feed provides one.
            if(rowId && item?.id && String(item.id)===rowId) return rankValue;
            // First use the existing alias-aware matcher.
            if(rowName && teamMatches(rankName,rowName)) return rankValue;
            // Stats Perform names usually omit the mascot while ESPN includes it.
            // Match when one normalized name is the full leading school name of the other.
            // Guard Montana vs Montana State so the Bobcats can never inherit Montana's rank.
            if(rowNorm && rankNorm && rowNorm!==rankNorm){
              const montanaStatePair=(rowNorm.includes('montanastate')||rankNorm.includes('montanastate')) && (rowNorm.includes('montana')||rankNorm.includes('montana'));
              if(!montanaStatePair && (rowNorm.startsWith(rankNorm)||rankNorm.startsWith(rowNorm))) return rankValue;
            }
          }
          return '';
        };
        const rankForTeam=rankForTeamForRow(team);
        const rankBadge=rankForTeam?`<span class="fcs-team-rank">#${escapeHtml(rankForTeam)}</span>`:'';
        return `<div class="fcs-top-team-row">${logo?`<img src="${escapeHtml(logo)}" alt="" loading="lazy">`:''}<span><span class="fcs-team-rank-wrap">${rankBadge}</span><span class="fcs-team-name">${escapeHtml(name)}</span></span><strong>${escapeHtml(x?.score??team?.score??'—')}</strong></div>`;
      };
      if(ev){
        const away=(ev.teams||[]).find(x=>x.homeAway==='away') || (ev.teams||[])[0];
        const home=(ev.teams||[]).find(x=>x.homeAway==='home') || (ev.teams||[])[1];
        const statusLabel=ev.completed ? 'FINAL' : (ev.state==='in' ? statusText(ev) : (ev.date?new Date(ev.date).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'TBA'));
        return `<div class="fcs-rank-card ${cardClass}"><div class="fcs-top-matchup">${teamRow(away)}${teamRow(home)}<small>${escapeHtml(statusLabel)}</small></div></div>`;
      }
      const fallbackLogo=t.logo||t.logo_url||'';
      const fallbackRank=String(t.rank||'').trim();
      const fallbackRankBadge=fallbackRank?`<span class="fcs-team-rank">#${escapeHtml(fallbackRank)}</span>`:'';
      const fallbackRow=`<div class="fcs-top-team-row">${fallbackLogo?`<img src="${escapeHtml(fallbackLogo)}" alt="" loading="lazy">`:''}<span><span class="fcs-team-rank-wrap">${fallbackRankBadge}</span><span class="fcs-team-name">${escapeHtml(t.team)}</span></span><strong>—</strong></div>`;
      return `<div class="fcs-rank-card ${cardClass}"><div class="fcs-top-matchup">${fallbackRow}<small>${escapeHtml(t.record||'')} • NO GAME THIS WEEK</small></div></div>`;
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
