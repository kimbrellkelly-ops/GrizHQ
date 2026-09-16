/* Legacy compatibility: scoreboard data is no longer fetched here.
   The dedicated scoreboard/scorebar-render.js owns the header score strip. */
(function(){
  'use strict';
  function boot(){
    const games=document.getElementById('score-games');
    const prev=document.querySelector('.v2-score-prev');
    const next=document.querySelector('.v2-score-next');
    if(!games || games.dataset.scrollOnlyReady==='1') return;
    games.dataset.scrollOnlyReady='1';
    if(prev) prev.addEventListener('click',e=>{e.preventDefault();games.scrollBy({left:-Math.max(280,games.clientWidth*.8),behavior:'smooth'});});
    if(next) next.addEventListener('click',e=>{e.preventDefault();games.scrollBy({left:Math.max(280,games.clientWidth*.8),behavior:'smooth'});});
    games.addEventListener('wheel',e=>{if(Math.abs(e.deltaY)>Math.abs(e.deltaX)){e.preventDefault();games.scrollLeft+=e.deltaY;}},{passive:false});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
