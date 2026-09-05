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
    if (srcEl && next.url) { srcEl.href = next.url; srcEl.textContent = "Opponent information ↗"; }

    // Keep the compact header game bar synchronized with the same next-game data.
    const hgKicker = document.getElementById("header-gamebar-kicker");
    const hgOpp = document.getElementById("header-gamebar-opponent");
    const hgDate = document.getElementById("header-gamebar-date");
    const hgVenue = document.getElementById("header-gamebar-venue");
    if (hgKicker) hgKicker.textContent = "NEXT GAME";
    if (hgOpp) hgOpp.textContent = (next.opponent || "OPPONENT").toUpperCase();
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
  const gamesEl=document.getElementById('fcs-games');
  const weekEl=document.getElementById('fcs-week-filter');
  const statusEl=document.getElementById('fcs-status');
  const labelEl=document.getElementById('fcs-all-label');
  const refreshEl=document.getElementById('fcs-refresh');
  if(!topEl || !gamesEl || !weekEl) return;

  const weeks=[
    ['2026-08-27','2026-08-30','WEEK 0 • AUG 27–30'],
    ['2026-09-03','2026-09-06','WEEK 1 • SEP 3–6'],
    ['2026-09-10','2026-09-13','WEEK 2 • SEP 10–13'],
    ['2026-09-17','2026-09-20','WEEK 3 • SEP 17–20'],
    ['2026-09-24','2026-09-27','WEEK 4 • SEP 24–27'],
    ['2026-10-01','2026-10-04','WEEK 5 • OCT 1–4'],
    ['2026-10-08','2026-10-11','WEEK 6 • OCT 8–11'],
    ['2026-10-15','2026-10-18','WEEK 7 • OCT 15–18'],
    ['2026-10-22','2026-10-25','WEEK 8 • OCT 22–25'],
    ['2026-10-29','2026-11-01','WEEK 9 • OCT 29–NOV 1'],
    ['2026-11-05','2026-11-08','WEEK 10 • NOV 5–8'],
    ['2026-11-12','2026-11-15','WEEK 11 • NOV 12–15'],
    ['2026-11-19','2026-11-22','WEEK 12 • NOV 19–22']
  ];
  if(!weekEl.dataset.ready){
    weeks.forEach((w,i)=>{const o=document.createElement('option');o.value=i;o.textContent=w[2];weekEl.appendChild(o);});
    weekEl.dataset.ready='1';
  }
  const now=new Date();
  let current=weeks.findIndex(w=>now>=new Date(w[0]+'T00:00:00') && now<=new Date(w[1]+'T23:59:59'));
  if(current<0) current=0;
  if(!weekEl.dataset.userChanged) weekEl.value=String(current);

  let localData={};
  try{localData=await (await fetch('data.json?ts='+Date.now(),{cache:'no-store'})).json();}catch(e){}
  const top20=Array.isArray(localData.fcs_top20)?localData.fcs_top20:[];
  const rankDate=document.getElementById('fcs-rankings-date');
  if(rankDate && localData.fcs_rankings_date) rankDate.textContent='Stats Perform • '+localData.fcs_rankings_date;

  function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');}
  function findTeam(name,events){
    const n=norm(name); return events.find(ev=>ev.competitions?.[0]?.competitors?.some(c=>norm(c.team?.displayName).includes(n)||n.includes(norm(c.team?.displayName)))) || null;
  }
  function statusText(ev){const c=ev.competitions?.[0]; const st=c?.status?.type; if(st?.completed) return 'FINAL'; if(st?.state==='in') return c.status?.type?.shortDetail||'LIVE'; return c?.date?new Date(c.date).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'}):'TBA';}
  function scoreLine(ev,name){
    if(!ev) return '<small>NO GAME</small>';
    const c=ev.competitions?.[0]; const teams=c?.competitors||[]; const me=teams.find(x=>norm(x.team?.displayName).includes(norm(name))||norm(name).includes(norm(x.team?.displayName)));
    if(!me) return '<small>'+escapeHtml(statusText(ev))+'</small>';
    const other=teams.find(x=>x!==me);
    if(c?.status?.type?.completed || c?.status?.type?.state==='in') return `${me.score ?? '0'}–${other?.score ?? '0'}<small>${escapeHtml(statusText(ev))}</small>`;
    return `<small>${escapeHtml(statusText(ev))}</small>`;
  }
  function gameLabel(ev){
    const c=ev.competitions?.[0]; const teams=c?.competitors||[]; const away=teams.find(x=>x.homeAway==='away'); const home=teams.find(x=>x.homeAway==='home');
    return {away:away?.team?.shortDisplayName||away?.team?.displayName||'Away',home:home?.team?.shortDisplayName||home?.team?.displayName||'Home',time:statusText(ev),venue:c?.venue?.fullName||''};
  }
  async function draw(){
    const w=weeks[Number(weekEl.value)||0];
    statusEl.textContent='Loading FCS scores…';
    gamesEl.innerHTML='<div class="fcs-loading">Loading FCS games…</div>';
    try{
      const startDate=w[0].replace(/-/g,''); const endDate=w[1].replace(/-/g,'');
      const url=`https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates=${startDate}-${endDate}&groups=81&limit=500`;
      const res=await fetch(url,{cache:'no-store'}); if(!res.ok) throw new Error('ESPN '+res.status);
      const payload=await res.json(); const events=Array.isArray(payload.events)?payload.events:[];
      statusEl.textContent=`${events.length} FCS games • live data`;
      labelEl.textContent=w[2];

      topEl.innerHTML=top20.map(t=>{
        const ev=findTeam(t.team,events); const isGriz=norm(t.team)==='montana'; const isBigSky=['Montana State','Montana','UC Davis','Northern Arizona','Idaho State','Southern Utah','Cal Poly'].includes(t.team);
        const cardClass=isGriz?'griz':(isBigSky?'bigsky':'');
        const detail=ev?gameLabel(ev):null;
        let matchup='';
        if(detail) matchup=`${escapeHtml(detail.away)} @ ${escapeHtml(detail.home)}`;
        else matchup='No game this week';
        return `<div class="fcs-rank-card ${cardClass}"><span class="fcs-rank">${t.rank}</span><div class="fcs-rank-team"><b>${escapeHtml(t.team)}</b><small>${escapeHtml(t.record||'')} ${matchup?'• '+matchup:''}</small></div><span class="fcs-rank-score">${scoreLine(ev,t.team)}</span></div>`;
      }).join('');

      if(!events.length){gamesEl.innerHTML='<div class="fcs-empty"><b>No FCS games found for this week.</b><br>Try another week from the dropdown.</div>';return;}
      const rows=events.map(ev=>{
        const d=gameLabel(ev); const c=ev.competitions?.[0]; const st=c?.status?.type; const state=st?.state==='in'?'live':(st?.completed?'final':'scheduled');
        const scores=(c?.competitors||[]).map(x=>`${escapeHtml(x.team?.shortDisplayName||x.team?.displayName||'')} ${escapeHtml(x.score??'')}`).join(' • ');
        const tv=(c?.broadcasts||[]).flatMap(b=>b.names||[]).slice(0,2).join(', ');
        return `<div class="fcs-game ${state}"><div class="fcs-time">${escapeHtml(d.time)}</div><div class="fcs-matchup"><b>${escapeHtml(d.away)} @ ${escapeHtml(d.home)}</b><small>${scores}</small></div><div class="fcs-score">${escapeHtml(st?.completed?'FINAL':st?.state==='in'?(st.shortDetail||'LIVE'):'')}</div><div class="fcs-tv">${escapeHtml(tv)}</div></div>`;
      }).join('');
      gamesEl.innerHTML=rows;
    }catch(e){
      statusEl.textContent='Score feed temporarily unavailable';
      gamesEl.innerHTML='<div class="fcs-empty"><b>Could not load FCS scores right now.</b><br>The Top 20 is still available. Use Refresh Scores to try again.</div>';
      console.warn('FCS scoreboard error',e);
    }
  }
  weekEl.onchange=()=>{weekEl.dataset.userChanged='1';draw();};
  if(refreshEl) refreshEl.onclick=draw;
  draw();
  setInterval(()=>{const d=new Date(); if(d.getDay()>=4) draw();},60000);
}
renderFCSScoreboard();
