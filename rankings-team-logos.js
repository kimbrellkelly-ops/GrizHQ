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
    "Lamar":"https://a.espncdn.com/i/teamlogos/ncaa/500/2320.png",
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
  function addScoreLogos(root){if(!root)return;root.querySelectorAll('.score-team-line').forEach(line=>{const nameEl=line.querySelector('b');if(!nameEl)return;const name=String(nameEl.textContent||'').replace(/^@\s*/,'').trim();const url=LOGOS[key(name)];if(url)addImage(line,url,'score-team-logo',name+' logo');});}
  function fixRankingsTitle(){document.querySelectorAll('h1,h2,h3').forEach(title=>{const text=String(title.textContent||'').replace(/\s+/g,' ').trim();if(/^Top 20\s*[—-]\s*Coaches & Media$/i.test(text))title.textContent='Top 25 — Coaches & Media';});}
  function fixHome(){
    const next=document.querySelector('.v2-home-next-match');
    if(next)next.innerHTML='<div><strong>GRIZ</strong><small>MONTANA<br>3–0</small></div><div><b>Sat, Sep 19<br>9:00 PM MT</b><small>USA Sports</small></div><div><strong>OSU</strong><small>OREGON STATE<br>0–2</small></div>';
    const venue=document.querySelector('.v2-home-next p');
    if(venue)venue.textContent='Reser Stadium · Corvallis, OR';
    const feature=document.querySelector('.v2-feature-overlay');
    if(feature){const h=feature.querySelector('h1'),p=feature.querySelector('p');if(h)h.textContent='Griz head to Corvallis to face Oregon State';if(p)p.textContent='Montana enters the first FBS matchup of the season at 3–0 and travels to Reser Stadium for a Saturday night game against the 0–2 Beavers.';}
    const story=document.querySelector('.v2-story-grid .v2-story:nth-child(3) h3');
    if(story)story.textContent='What to know: Montana at Oregon State';
    const snapshot=document.querySelector('.v2-snapshot-grid');
    if(snapshot)snapshot.innerHTML='<div><b>3–0</b><small>Record</small></div><div><b>#3</b><small>FCS Rank</small></div><div><b>1–0</b><small>Big Sky</small></div>';
    const nextUp=document.getElementById('next-up');
    if(nextUp){
      const title=nextUp.querySelector('.ghq-nu-hero-top h1 span');if(title)title.textContent='OREGON STATE';
      const pill=nextUp.querySelector('.ghq-nu-game-pill');if(pill)pill.innerHTML='<b>SEP 19</b><span>9:00 PM MT</span><small>RESER STADIUM · CORVALLIS, OR</small>';
      const teams=nextUp.querySelectorAll('.ghq-nu-team');
      if(teams.length>=2){const griz=teams[0],osu=teams[1];const gr=griz.querySelector('.ghq-nu-rank');if(gr)gr.textContent='#3';const gp=griz.querySelector('p');if(gp)gp.textContent='3–0 • 1–0 BIG SKY';const op=osu.querySelector('.ghq-nu-logo img');if(op){op.src=LOGOS['Oregon State'];op.alt='Oregon State Beavers';}const or=osu.querySelector('.ghq-nu-rank');if(or)or.textContent='OPPONENT';const oh=osu.querySelector('h2');if(oh)oh.textContent='OREGON STATE';const opr=osu.querySelector('p');if(opr)opr.textContent='0–2 • PAC-12';}
      nextUp.querySelectorAll('a').forEach(a=>{if(/UTAH TECH/i.test(a.textContent)){a.textContent=a.textContent.replace(/UTAH TECH/ig,'OREGON STATE');a.href='https://osubeavers.com/sports/football';}if(/utahtechtrailblazers\.com/i.test(a.href)){a.href='https://osubeavers.com/sports/football';}});
    }
  }
  function run(){addLogos(document.getElementById('coaches-poll'));addLogos(document.getElementById('media-poll'));addScheduleLogos(document.getElementById('schedule-list'));addScoreLogos(document.getElementById('bigsky-table'));fixRankingsTitle();fixHome();}
  const style=document.createElement('style');style.textContent='.ranking-team-logo,.schedule-team-logo,.score-team-logo{width:26px;height:26px;object-fit:contain;flex:0 0 26px;margin-right:.35rem}.rank-team-name{min-width:0}.schedule-team-line{display:flex;align-items:center;gap:.25rem}';document.head.appendChild(style);
  const observer=new MutationObserver(run);
  function start(){run();['coaches-poll','media-poll','schedule-list','bigsky-table','v2-home','next-up'].forEach(id=>{const el=document.getElementById(id);if(el)observer.observe(el,{childList:true,subtree:true});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();