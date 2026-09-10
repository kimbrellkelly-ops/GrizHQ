(function(){
  const LOGOS={
    "Montana State":"https://a.espncdn.com/i/teamlogos/ncaa/500/147.png",
    "South Dakota State":"https://a.espncdn.com/i/teamlogos/ncaa/500/2571.png",
    "Montana":"https://a.espncdn.com/i/teamlogos/ncaa/500/149.png",
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
    "Harvard":"https://a.espncdn.com/i/teamlogos/ncaa/500/108.png"
  };
  const aliases={"Montana St.":"Montana State","South Dakota St.":"South Dakota State","Idaho St.":"Idaho State"};
  function key(name){const n=String(name||'').trim();return aliases[n]||n;}
  function addLogos(root){
    if(!root)return;
    root.querySelectorAll('li').forEach(li=>{
      if(li.querySelector('.ranking-team-logo'))return;
      const nameEl=li.querySelector('.rank-team-name');
      if(!nameEl)return;
      const url=LOGOS[key(nameEl.textContent)];
      if(!url)return;
      const img=document.createElement('img');
      img.className='ranking-team-logo';
      img.src=url;
      img.alt='';
      img.loading='lazy';
      img.width=26; img.height=26;
      img.addEventListener('error',()=>img.remove(),{once:true});
      nameEl.parentNode.insertBefore(img,nameEl);
    });
  }
  function run(){addLogos(document.getElementById('coaches-poll'));addLogos(document.getElementById('media-poll'));}
  const style=document.createElement('style');
  style.textContent='.ranking-team-logo{width:26px;height:26px;object-fit:contain;flex:0 0 26px;margin-right:.15rem}.rank-team-name{min-width:0}';
  document.head.appendChild(style);
  const observer=new MutationObserver(run);
  function start(){run();const a=document.getElementById('coaches-poll'),b=document.getElementById('media-poll');if(a)observer.observe(a,{childList:true,subtree:true});if(b)observer.observe(b,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();