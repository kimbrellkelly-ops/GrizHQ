(function(){
  const LOGOS={
    "Montana":"https://a.espncdn.com/i/teamlogos/ncaa/500/149.png",
    "Montana State":"https://a.espncdn.com/i/teamlogos/ncaa/500/147.png",
    "South Dakota State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2571.png",
    "Illinois State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2287.png",
    "Tarleton State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2627.png",
    "UC Davis":"https://a.espncdn.com/i/teamlogos/ncaa/500/302.png",
    "Youngstown State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2754.png",
    "Rhode Island":"https://a.espncdn.com/i/teamlogos/ncaa/500/227.png",
    "North Dakota":"https://a.espncdn.com/i/teamlogos/ncaa/500/155.png",
    "Lehigh":"https://a.espncdn.com/i/teamlogos/ncaa/500/2329.png",
    "Stephen F. Austin":"https://a.espncdn.com/i/teamlogos/ncaa/500/2617.png",
    "South Dakota":"https://a.espncdn.com/i/teamlogos/ncaa/500/233.png",
    "Tennessee Tech":"https://a.espncdn.com/i/teamlogos/ncaa/500/2635.png",
    "Austin Peay":"https://a.espncdn.com/i/teamlogos/ncaa/500/2046.png",
    "Mercer":"https://a.espncdn.com/i/teamlogos/ncaa/500/2382.png",
    "Villanova":"https://a.espncdn.com/i/teamlogos/ncaa/500/222.png",
    "Yale":"https://a.espncdn.com/i/teamlogos/ncaa/500/43.png",
    "William & Mary":"https://a.espncdn.com/i/teamlogos/ncaa/500/2729.png",
    "Northern Arizona":"https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png",
    "Abilene Christian":"https://a.espncdn.com/i/teamlogos/ncaa/500/2000.png",
    "South Carolina State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2569.png",
    "Richmond":"https://a.espncdn.com/i/teamlogos/ncaa/500/257.png",
    "Central Arkansas":"https://a.espncdn.com/i/teamlogos/ncaa/500/2110.png",
    "Southern Illinois":"https://a.espncdn.com/i/teamlogos/ncaa/500/79.png",
    "West Florida":"https://a.espncdn.com/i/teamlogos/ncaa/500/110242.png",
    "Idaho State":"https://a.espncdn.com/i/teamlogos/ncaa/500/304.png",
    "Harvard":"https://a.espncdn.com/i/teamlogos/ncaa/500/108.png",
    "Southern Utah":"https://a.espncdn.com/i/teamlogos/ncaa/500/253.png",
    "Drake":"https://a.espncdn.com/i/teamlogos/ncaa/500/2181.png",
    "Utah Tech":"https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png",
    "Oregon State":"https://a.espncdn.com/i/teamlogos/ncaa/500/204.png",
    "Northern Colorado":"https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png",
    "Idaho":"https://a.espncdn.com/i/teamlogos/ncaa/500/70.png",
    "Eastern Washington":"https://a.espncdn.com/i/teamlogos/ncaa/500/331.png",
    "Portland State":"https://a.espncdn.com/i/teamlogos/ncaa/500/279.png",
    "Incarnate Word":"https://a.espncdn.com/i/teamlogos/ncaa/500/2916.png",
    "Monmouth":"https://a.espncdn.com/i/teamlogos/ncaa/500/2405.png",
    "Cal Poly":"https://a.espncdn.com/i/teamlogos/ncaa/500/13.png",
    "Weber State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2692.png",
    "Sacramento State":"https://a.espncdn.com/i/teamlogos/ncaa/500/16.png"
  };
  const aliases={"Montana St.":"Montana State","South Dakota St.":"South Dakota State","Idaho St.":"Idaho State","UC-Davis":"UC Davis","N. Colorado":"Northern Colorado","N. Arizona":"Northern Arizona","E. Washington":"Eastern Washington","Portland St.":"Portland State","Cal Poly SLO":"Cal Poly","Incarnate Word Cardinals":"Incarnate Word"};
  function key(name){const n=String(name||'').replace(/\s+/g,' ').trim();return aliases[n]||n;}
  function addImage(parent,url,className,alt){if(!parent||!url||parent.querySelector('.'+className))return;const img=document.createElement('img');img.className=className;img.src=url;img.alt=alt||'';img.loading='lazy';img.width=26;img.height=26;img.addEventListener('error',()=>img.remove(),{once:true});parent.insertBefore(img,parent.firstChild);}
  function addLogos(root){if(!root)return;root.querySelectorAll('li').forEach(li=>{const nameEl=li.querySelector('.rank-team-name');if(!nameEl)return;const url=LOGOS[key(nameEl.textContent)];if(url)addImage(nameEl.parentNode,url,'ranking-team-logo','');});}
  function addScheduleLogos(root){if(!root)return;root.querySelectorAll('.schedule-team-line').forEach(line=>{const nameEl=line.querySelector('b');if(!nameEl)return;const name=String(nameEl.textContent||'').replace(/^@\s*/,'').trim();const url=LOGOS[key(name)];if(url)addImage(line,url,'schedule-team-logo',name+' logo');});}
  function fixRankingsTitle(){document.querySelectorAll('h1,h2,h3').forEach(title=>{const text=String(title.textContent||'').replace(/\s+/g,' ').trim();if(/^Top 20\s*[—-]\s*Coaches & Media$/i.test(text))title.textContent='Top 25 — Coaches & Media';});}
  function setText(selector,text){const el=document.querySelector(selector);if(el&&el.textContent!==text)el.textContent=text;}
  function syncHomepage(){
    setText('.v2-home-next-match > div:nth-child(1) small','MONTANA 3–0');
    const center=document.querySelector('.v2-home-next-match > div:nth-child(2)');
    if(center)center.innerHTML='<b>Sat, Sep 19<br>9:00 PM MT</b><small>USA Sports</small>';
    const opp=document.querySelector('.v2-home-next-match > div:nth-child(3) small');
    if(opp)opp.textContent='OREGON STATE 0–2';
    setText('.v2-home-next p','Reser Stadium · Corvallis, OR');
    setText('.v2-feature-overlay h1','Griz head to Corvallis for Oregon State matchup');
    setText('.v2-feature-overlay p','Montana takes its 3–0 record on the road Saturday night to face Oregon State at Reser Stadium.');
    setText('.v2-story-grid .v2-story:nth-child(3) h3','What to know: Montana at Oregon State');
    const headlineLinks=document.querySelectorAll('.v2-headlines a');
    headlineLinks.forEach(a=>{if(a.textContent.includes('Utah Tech scouting notes'))a.firstChild.textContent='Opponent report: Oregon State scouting notes';});
    const snap=document.querySelectorAll('.v2-snapshot-grid b');
    if(snap.length>=3){snap[0].textContent='3–0';snap[1].textContent='#3';snap[2].textContent='1–0';}
    setText('.ghq-next-up h1 span','OREGON STATE');
    setText('.ghq-game-pill b','SEP 19');
    setText('.ghq-nu-game-pill b','SEP 19');
    setText('.ghq-nu-game-pill span','9:00 PM MT');
    setText('.ghq-nu-game-pill small','RESER STADIUM · CORVALLIS, OR');
    setText('.ghq-nu-team.is-griz .ghq-nu-rank','#3');
    setText('.ghq-nu-team.is-griz p','3–0 • 1–0 BIG SKY');
    setText('.ghq-nu-team.is-opponent h2','OREGON STATE');
    setText('.ghq-nu-team.is-opponent p','0–2');
    const osu=document.querySelector('.ghq-nu-team.is-opponent .ghq-nu-logo img');
    if(osu){osu.src=LOGOS['Oregon State'];osu.alt='Oregon State Beavers';}
  }
  function addScoreLogos(root){if(!root)return;root.querySelectorAll('.score-team-line').forEach(line=>{const nameEl=line.querySelector('b,span');if(!nameEl)return;const url=LOGOS[key(nameEl.textContent)];if(url)addImage(line,url,'score-team-logo',nameEl.textContent+' logo');});}
  function run(){addLogos(document.getElementById('coaches-poll'));addLogos(document.getElementById('media-poll'));addScheduleLogos(document.getElementById('schedule-list'));addScoreLogos(document.getElementById('bigsky-table'));fixRankingsTitle();syncHomepage();}
  const style=document.createElement('style');style.textContent='.ranking-team-logo,.schedule-team-logo,.score-team-logo{width:26px;height:26px;object-fit:contain;flex:0 0 26px;margin-right:.35rem}.rank-team-name{min-width:0}.schedule-team-line{display:flex;align-items:center;gap:.25rem}';document.head.appendChild(style);
  const observer=new MutationObserver(run);
  function start(){run();['coaches-poll','media-poll','schedule-list','bigsky-table'].forEach(id=>{const el=document.getElementById(id);if(el)observer.observe(el,{childList:true,subtree:true});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();