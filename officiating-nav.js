/* Griz HQ — surgical Officiating Intelligence entry point.
   Loaded by the production shell when included; kept separate from app.js. */
(function(){
  function install(){
    const nav=document.querySelector('header.site-header nav.nav');
    if(!nav || nav.querySelector('[data-officiating-link]')) return;
    const a=document.createElement('a');
    a.href='officiating.html';
    a.target='_self';
    a.textContent='OFFICIATING';
    a.setAttribute('data-officiating-link','1');
    a.setAttribute('aria-label','Officiating Intelligence');
    nav.appendChild(a);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install); else install();
})();
