(function(){
"use strict";
const C=window.GRIZ_SCOREBOARD_CONFIG;if(!C)return;
const esc=s=>String(s??"").replace(/[&<>\"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const clean=s=>String(s||"").replace(/\s*\([^)]*\)\s*$/,"").replace(/\s+/g," ").trim();
const norm=s=>clean(s).toLowerCase().replace(/[^a-z0-9]/g,"");
const A=[["southdakotastate",["southdakotastate","sdstate","s dakota st","s dakota state"]],["southdakota",["southdakota","s dakota"]],["montanastate",["montanastate","montanastatebobcats"]],["montana",["montana","montanagrizzlies"]],["idahostate",["idahostate","idahostatebengals"]],["idaho",["idaho","idahovandals"]],["youngstownstate",["youngstownstate","youngstownst"]],["stephenfaustin",["stephenfaustin","sfa"]],["williammary",["williammary","williamandmary"]],["westflorida",["westflorida","westfloridaargos"]],["southernillinois",["southernillinois","southernillinoissalukis"]],["easternwashington",["easternwashington","easternwashingtoneagles"]],["northernarizona",["northernarizona","northernarizonalumberjacks","nau"]],["northerncolorado",["northerncolorado","northerncoloradobears"]],["portlandstate",["portlandstate","portlandstatevikings"]],["weberstate",["weberstate","weberstatewildcats"]],["southernutah",["southernutah","southernutahthunderbirds"]],["utahtech",["utahtech","utahtechtrailblazers"]],["calpoly",["calpoly","calpolymustangs"]],["ucdavis",["ucdavis","ucdavisaggies"]]];
const canonical=s=>{const x=norm(s);for(const [k,v] of A)if(x===k||v.includes(x))return k;return x;};
const name=t=>t?.name||t?.short||t?.abbreviation||"Team";
const logo=t=>t?.logo||(t?.id?`https://a.espncdn.com/i/teamlogos/ncaa/500/${encodeURIComponent(t.id)}.png`:"");
const status=e=>e?.status?.completed?"FINAL":e?.status?.state==="in"?(e.status.shortDetail||"LIVE"):(e?.status?.shortDetail||e?.status?.detail||"SCHEDULED");
const dtext=s=>{const d=new Date(s);return Number.isNaN(d.getTime())?"":d.toLocaleDateString("en-US",{weekday:"short",month:"short",day:"numeric"});};
const rankOf=(n,rs)=>{const c=canonical(n),r=rs.find(x=>canonical(x.team)===c);return r?`#${r.rank}`:"";};
const eventFor=(r,es)=>{const c=canonical(clean(r.team));return es.find(e=>(e.teams||[]).some(t=>canonical(name(t))===c))||null;};
function card(e,rs){const ts=e.teams||[],a=ts.find(t=>t.homeAway==="away")||ts[0]||{},h=ts.find(t=>t.homeAway==="home")||ts[1]||{};
const row=t=>`<div class="ghq-score-team"><div class="ghq-score-team-main">${logo(t)?`<img class="ghq-score-logo" src="${esc(logo(t))}" alt="" loading="lazy">`:""}<span>${rankOf(name(t),rs)?`<span class="ghq-score-team-rank">${esc(rankOf(name(t),rs))}</span>`:""}<span class="ghq-score-team-name">${esc(name(t))}</span></span></div><span class="ghq-score-team-score">${esc(t.score??"—")}</span></div>`;
const href=e.id?`https://www.espn.com/college-football/game/_/gameId/${encodeURIComponent(e.id)}`:"#";
return `<a class="ghq-score-card" href="${href}" target="_blank" rel="noopener"><div class="ghq-score-top"><span>${esc(dtext(e.date))}</span><span class="ghq-score-network">${esc((e.broadcasts||[])[0]||"ESPN")}</span></div>${row(a)}${row(h)}<div class="ghq-score-bottom"><span class="ghq-score-status">${esc(status(e))}</span><span>${esc(e.venue||"")}</span></div></a>`;}
function empty(r,complete){return `<div class="ghq-score-card ghq-score-empty"><strong>${complete?"BYE / NO GAME THIS WEEK":"SCHEDULE DATA PENDING"}</strong><span>#${esc(r.rank)} ${esc(clean(r.team))}</span></div>`;}
function css(){if(document.getElementById("ghq-score-css"))return;const l=document.createElement("link");l.id="ghq-score-css";l.rel="stylesheet";l.href="scoreboard/scoreboard.css?v=final2";document.head.appendChild(l);}
function currentWeek(){const n=new Date();const i=C.weeks.findIndex(w=>n>=new Date(w[0]+"T00:00:00")&&n<=new Date(w[1]+"T23:59:59"));if(i>=0)return i;const f=C.weeks.findIndex(w=>new Date(w[0]+"T00:00:00")>n);return f>=0?f:C.weeks.length-1;}
async function render(){css();const top=document.getElementById("fcs-top20"),big=document.getElementById("bigsky-score-games"),week=document.getElementById("fcs-week-filter"),st=document.getElementById("fcs-status"),refresh=document.getElementById("fcs-refresh");if(!top||!big||!week)return;
if(!week.dataset.ghqReady){C.weeks.forEach((w,i)=>{const o=document.createElement("option");o.value=i;o.textContent=w[2];week.appendChild(o)});week.value=String(currentWeek());week.dataset.ghqReady="1";week.addEventListener("change",render);}
if(refresh&&!refresh.dataset.ghqBound){refresh.dataset.ghqBound="1";refresh.addEventListener("click",render);}
const i=Number(week.value)||0;const w=C.weeks[i];top.innerHTML="<div class='ghq-score-empty'><strong>Loading verified scoreboard…</strong></div>";big.innerHTML="";
try{const data=await fetch(`scoreboard/scoreboard-data.json?ts=${Date.now()}`,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("scoreboard cache "+r.status);return r.json()});
const wd=(data.weeks||[]).find(x=>x.index===i);if(!wd)throw Error("selected week has no generated cache");
const rs=(data.rankings||[]).slice(0,25),f=wd.fcsEvents||[],b=wd.bigSkyEvents||[];
top.innerHTML=`<div class="ghq-scoreboard-grid">${rs.map(r=>{const e=eventFor(r,f);return e?card(e,rs):empty(r,wd.complete)}).join("")}</div>`;
big.innerHTML=b.length?`<div class="ghq-scoreboard-grid">${b.map(e=>card(e,rs)).join("")}</div>`:`<div class="ghq-score-empty"><strong>NO BIG SKY GAMES THIS WEEK</strong></div>`;
const rd=document.getElementById("fcs-rankings-date");if(rd&&data.rankingsDate)rd.textContent=`Stats Perform • ${data.rankingsDate}`;
if(st)st.textContent=`Verified ESPN cache • ${wd.fcsEventCount} FCS events • ${wd.bigSkyEventCount} Big Sky games`;
}catch(e){console.error("Griz scoreboard",e);top.innerHTML="<div class='ghq-score-error'><strong>SCOREBOARD DATA UNAVAILABLE</strong><span>GitHub Actions has not produced a verified cache yet.</span></div>";big.innerHTML="<div class='ghq-score-error'><strong>SCOREBOARD DATA UNAVAILABLE</strong></div>";if(st)st.textContent="Scoreboard cache unavailable";}}
window.GrizScoreboard={render};window.renderFCSScoreboard=render;render();
})();