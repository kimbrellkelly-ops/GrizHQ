(function(){
  function load(src,onload){const s=document.createElement('script');s.src=src;s.onload=onload;s.onerror=function(){console.error('Griz HQ script failed to load:',src);};document.head.appendChild(s);}
  load('app-core.js?v=20260909-rankings-logos1',function(){load('rankings-team-logos.js?v=20260909-rankings-logos1');});
})();
