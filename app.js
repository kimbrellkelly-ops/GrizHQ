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

async function renderBigSkyAndOpponent(){try{const d=await (await fetch("data.json?ts="+Date.now(),{cache:"no-store"})).json();const t=document.getElementById("bigsky-table"),ts=document.getElementById("bigsky-team-filter"),ds=document.getElementById("bigsky-date-filter");if(t&&d.big_sky_schedule){const weeks=(d.schedule||[]).filter(g=>g.date&&!g.result).map(g=>({date:g.date,time:g.time,opponent:g.opponent}));const current=weeks[0]?.date||"Sep 5";const uniqueWeeks=[];weeks.forEach(g=>{if(!uniqueWeeks.some(x=>x.date===g.date))uniqueWeeks.push(g)});ds.innerHTML=uniqueWeeks.map((g,i)=>`<option value="${escapeHtml(g.date)}">${i===0?"CURRENT WEEK • ":"WEEK "+(i+1)+" • "}${escapeHtml(g.date)}</option>`).join("");(d.big_sky_teams||[]).forEach(x=>{let o=document.createElement("option");o.value=x;o.textContent=x.toUpperCase();ts.appendChild(o)});function draw(){const selected=ds.value;let a=d.big_sky_schedule.filter(x=>x.date===selected);if(ts.value!=="ALL")a=a.filter(x=>x.away===ts.value||x.home===ts.value);const week=uniqueWeeks.find(x=>x.date===selected);let html='';if(!a.length){html=`<div class="bigsky-empty"><b>${selected===current?"CURRENT WEEK":"THIS WEEK"}</b><br>No Big Sky conference games are scheduled. Use the week dropdown to look ahead.</div>`}else{html='<div class="bigsky-row bigsky-head"><span>DATE</span><span>MATCHUP</span><span>TIME</span><span>TV</span></div>'+a.map(x=>'<div class="bigsky-row"><span>'+escapeHtml(x.date)+'</span><b>'+escapeHtml(x.away)+' @ '+escapeHtml(x.home)+'</b><span>'+escapeHtml(x.time)+'</span><span>'+escapeHtml(x.tv)+'</span></div>').join("")}t.innerHTML=html}ts.onchange=draw;ds.onchange=draw;draw()}const n=d.next_game?.opponent||"Drake",r=d.opponent_resources?.[n];if(r){document.getElementById("opponent-hub-name").textContent=n;document.getElementById("opp-title").textContent=n.toUpperCase();document.getElementById("opp-official").href=r.official;document.getElementById("opp-forum").href=r.forum;document.getElementById("opp-forum-label").textContent=r.label||"Fan discussion";document.getElementById("opp-media").href=r.media}}catch(e){console.warn(e)}}renderBigSkyAndOpponent();
