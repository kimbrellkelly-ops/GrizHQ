(function(){
  'use strict';
  const LOGOS={
    'Montana':'https://a.espncdn.com/i/teamlogos/ncaa/500/149.png',
    'Montana State':'https://a.espncdn.com/i/teamlogos/ncaa/500/147.png',
    'South Dakota State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2571.png',
    'Oregon State':'https://a.espncdn.com/i/teamlogos/ncaa/500/204.png',
    'Southern Utah':'https://a.espncdn.com/i/teamlogos/ncaa/500/253.png',
    'Drake':'https://a.espncdn.com/i/teamlogos/ncaa/500/2181.png',
    'Utah Tech':'https://a.espncdn.com/i/teamlogos/ncaa/500/3101.png',
    'UC Davis':'https://a.espncdn.com/i/teamlogos/ncaa/500/302.png',
    'Northern Colorado':'https://a.espncdn.com/i/teamlogos/ncaa/500/2458.png',
    'Northern Arizona':'https://a.espncdn.com/i/teamlogos/ncaa/500/2464.png',
    'Idaho':'https://a.espncdn.com/i/teamlogos/ncaa/500/70.png',
    'Eastern Washington':'https://a.espncdn.com/i/teamlogos/ncaa/500/331.png',
    'Portland State':'https://a.espncdn.com/i/teamlogos/ncaa/500/279.png',
    'Idaho State':'https://a.espncdn.com/i/teamlogos/ncaa/500/304.png',
    'Illinois State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2287.png',
    'Tarleton State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2627.png',
    'Youngstown State':'https://a.espncdn.com/i/teamlogos/ncaa/500/2754.png',
    'Rhode Island':'https://a.espncdn.com/i/teamlogos/ncaa/500/227.png',
    'North Dakota':'https://a.espncdn.com/i/teamlogos/ncaa/500/155.png',
    'Lehigh':'https://a.espncdn.com/i/teamlogos/ncaa/500/2329.png',
    'South Dakota':'https://a.espncdn.com/i/teamlogos/ncaa/500/233.png',
    'Yale':'https://a.espncdn.com/i/teamlogos/ncaa/500/43.png',
    'Harvard':'https://a.espncdn.com/i/teamlogos/ncaa/500/108.png'
  };
  const aliases={'Montana St.':'Montana State','South Dakota St.':'South Dakota State','Idaho St.':'Idaho State'};
  const key=s=>aliases[String(s||'').replace(/\s+/g,' ').trim()]||String(s||'').replace(/\s+/g,' ').trim();
  const text=(selector,value)=>{const el=document.querySelector(selector);if(el)el.textContent=value;};
  function homepage(){
    text('.v2-home-next-match > div:nth-child(1) small','MONTANA\n3–0');
    const center=document.querySelector('.v2-home-next-match > div:nth-child(2)');
    if(center)center.innerHTML='<b>Sat, Sep 19<br>9:00 PM MT</b><small>USA Sports</small>';
    text('.v2-home-next-match > div:nth-child(3) small','OREGON STATE\n0–2');
    text('.v2-home-next p','Reser Stadium · Corvallis, OR');
    text('.v2-feature-overlay h1','Griz head to Corvallis for Oregon State matchup');
    text('.v2-feature-overlay p','Montana takes its 3–0 record on the road Saturday night to face Oregon State at Reser Stadium.');
    text('.v2-story-grid .v2-story:nth-child(3) h3','What to know: Montana at Oregon State');
    document.querySelectorAll('.v2-headlines a').forEach(a=>{if(a.textContent.includes('Utah Tech scouting notes'))a.firstChild.textContent='Opponent report: Oregon State scouting notes';});
    const snap=document.querySelectorAll('.v2-snapshot-grid b');
    if(snap.length>=3){snap[0].textContent='3–0';snap[1].textContent='#3';snap[2].textContent='1–0';}
    text('.ghq-nu-hero h1 span','OREGON STATE');
    text('.ghq-nu-game-pill b','SEP 19');
    text('.ghq-nu-game-pill span','9:00 PM MT');
    text('.ghq-nu-game-pill small','RESER STADIUM · CORVALLIS, OR');
    text('.ghq-nu-team.is-griz .ghq-nu-rank','#3');
    text('.ghq-nu-team.is-griz p','3–0 • 1–0 BIG SKY');
    text('.ghq-nu-team.is-opponent h2','OREGON STATE');
    text('.ghq-nu-team.is-opponent p','0–2');
    const osu=document.querySelector('.ghq-nu-team.is-opponent .ghq-nu-logo img');
    if(osu){osu.src=LOGOS['Oregon State'];osu.alt='Oregon State Beavers';}
  }
  function logos(){
    document.querySelectorAll('.rank-team-name,.schedule-team-line b,.score-team-line b,.score-team-line span').forEach(el=>{
      const url=LOGOS[key(el.textContent)];if(!url||el.parentNode.querySelector('img.team-logo-fixed'))return;
      const img=document.createElement('img');img.className='team-logo-fixed';img.src=url;img.alt='';img.width=26;img.height=26;img.style.cssText='width:26px;height:26px;object-fit:contain;margin-right:.35rem';el.parentNode.insertBefore(img,el.parentNode.firstChild);
    });
  }
  function run(){homepage();logos();}
  function start(){run();new MutationObserver(run).observe(document.body,{childList:true,subtree:true});setInterval(run,1000);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();