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

async function renderBigSkyAndOpponent(){
  try{
    const d=await (await fetch("data.json?ts="+Date.now(),{cache:"no-store"})).json();
    const t=document.getElementById("bigsky-table"), ts=document.getElementById("bigsky-team-filter"), ds=document.getElementById("bigsky-date-filter");
    const games=d.big_sky_full_schedules||[];
    const teams=d.big_sky_teams||[];
    const weekLabels=["Aug 29","Sep 5","Sep 12","Sep 19","Sep 26","Oct 3","Oct 10","Oct 17","Oct 24","Oct 31","Nov 7","Nov 14","Nov 21"];
    const weekNames={"Aug 29":"Aug 28–29","Sep 5":"Sep 3–5","Sep 12":"Sep 12","Sep 19":"Sep 18–19","Sep 26":"Sep 26","Oct 3":"Oct 2–3","Oct 10":"Oct 10","Oct 17":"Oct 17","Oct 24":"Oct 24","Oct 31":"Oct 31","Nov 7":"Nov 7","Nov 14":"Nov 13–14","Nov 21":"Nov 21"};
    const monthNum={Aug:8,Sep:9,Oct:10,Nov:11};
    function dateObj(label){
      const [m,day]=label.split(" ");
      return new Date(2026,monthNum[m]-1,Number(day),12,0,0);
    }
    function weekForDate(label){
      const dt=dateObj(label);
      const saturday=new Date(dt);
      saturday.setDate(dt.getDate()+(6-dt.getDay()));
      return saturday.toLocaleDateString("en-US",{month:"short",day:"numeric"});
    }
    if(t&&games.length){
      if(ts && !ts.dataset.ready){
        teams.forEach(x=>{let o=document.createElement("option");o.value=x;o.textContent=x.toUpperCase();ts.appendChild(o)}); ts.dataset.ready="1";
      }
      if(ds && !ds.dataset.ready){
        weekLabels.forEach(x=>{let o=document.createElement("option");o.value=x;o.textContent=weekNames[x]||x;ds.appendChild(o)}); ds.dataset.ready="1";
      }
      const today=new Date();
      const saturday=new Date(today); saturday.setDate(today.getDate()+(6-today.getDay()));
      const currentWeek=saturday.toLocaleDateString("en-US",{month:"short",day:"numeric"});
      if(ds && weekLabels.includes(currentWeek)) ds.value=currentWeek; else if(ds) ds.value=weekLabels[0];

      function draw(){
        const selectedWeek=ds?.value||currentWeek;
        const selectedTeam=ts?.value||"ALL";
        const weekGames=games.filter(x=>weekForDate(x.date)===selectedWeek);
        const shownTeams=selectedTeam==="ALL"?teams:[selectedTeam];
        const rows=[];
        shownTeams.forEach(team=>{
          const tg=weekGames.filter(x=>x.team===team);
          if(!tg.length){
            rows.push('<div class="bigsky-row bye-row"><span>'+escapeHtml(selectedWeek)+'</span><b>'+escapeHtml(team)+'</b><span>BYE / NO GAME</span><span>—</span></div>');
          } else {
            tg.sort((a,b)=>dateObj(a.date)-dateObj(b.date));
            tg.forEach(x=>{
              const away=x.location==='Away';
              rows.push('<div class="bigsky-row"><span>'+escapeHtml(x.date)+'</span><b>'+escapeHtml(team)+'</b><span>'+(away?'@ ':'vs ')+escapeHtml(x.opponent)+(x.big_sky_game?' <small class="league-tag">BIG SKY</small>':'')+'</span><span>'+escapeHtml(x.time)+'</span></div>');
            });
          }
        });
        t.innerHTML='<div class="bigsky-row bigsky-head"><span>DATE</span><span>BIG SKY TEAM</span><span>OPPONENT</span><span>TIME</span></div>'+rows.join('');
      }
      if(ts) ts.onchange=draw; if(ds) ds.onchange=draw; draw();
    }
    const n=d.next_game?.opponent||"Drake",r=d.opponent_resources?.[n];
    if(r){document.getElementById("opponent-hub-name").textContent=n;document.getElementById("opp-title").textContent=n.toUpperCase();document.getElementById("opp-official").href=r.official;document.getElementById("opp-forum").href=r.forum;document.getElementById("opp-forum-label").textContent=r.label||"Fan discussion";document.getElementById("opp-media").href=r.media}
  }catch(e){console.warn(e)}
}
renderBigSkyAndOpponent();
