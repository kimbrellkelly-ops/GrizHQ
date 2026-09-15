from pathlib import Path

ROOT = Path(__file__).resolve().parent

css = ROOT / 'styles.css'
css_text = css.read_text(encoding='utf-8')
css_marker = '/* SCOREBAR HOTFIX 2026-09-15 */'
css_patch = '''\n\n/* SCOREBAR HOTFIX 2026-09-15 */\n.v2-scorebar{display:flex!important;align-items:stretch!important;gap:10px!important;min-width:0!important;overflow:hidden!important}\n.v2-score-games{display:flex!important;flex:1 1 auto!important;min-width:0!important;overflow-x:auto!important;overflow-y:hidden!important;gap:12px!important;scroll-behavior:smooth!important;scrollbar-width:thin!important;padding:2px 0 8px!important}\n.v2-score-games>*{flex:0 0 300px!important;min-width:300px!important}\n.v2-score-prev,.v2-score-next{flex:0 0 48px!important;z-index:2!important}\n@media(max-width:700px){.v2-score-games>*{flex-basis:260px!important;min-width:260px!important}.v2-score-prev,.v2-score-next{flex-basis:38px!important}}\n'''
if css_marker not in css_text:
    css.write_text(css_text + css_patch, encoding='utf-8')

html = ROOT / 'index.html'
html_text = html.read_text(encoding='utf-8')
replacements = {
    '<strong>GRIZ</strong><small>MONTANA<br>2–0</small>': '<strong>GRIZ</strong><small>MONTANA<br><span id="home-montana-record">—</span></small>',
    '<div><b>2–0</b><small>Record</small></div>': '<div><b id="home-snapshot-record">—</b><small>Record</small></div>',
}
for old, new in replacements.items():
    html_text = html_text.replace(old, new)
html.write_text(html_text, encoding='utf-8')

js = ROOT / 'app.js'
js_text = js.read_text(encoding='utf-8')
js_marker = '/* SCOREBAR HOTFIX 2026-09-15 */'
js_patch = r'''

/* SCOREBAR HOTFIX 2026-09-15 */
(function(){
  function wireScorebar(){
    const strip=document.querySelector('.v2-score-games');
    const prev=document.querySelector('.v2-score-prev');
    const next=document.querySelector('.v2-score-next');
    if(!strip||strip.dataset.hotfixWired==='1')return;
    strip.dataset.hotfixWired='1';
    const step=()=>Math.max(260,Math.floor(strip.clientWidth*.72));
    prev&&prev.addEventListener('click',()=>strip.scrollBy({left:-step(),behavior:'smooth'}));
    next&&next.addEventListener('click',()=>strip.scrollBy({left:step(),behavior:'smooth'}));
    strip.addEventListener('wheel',e=>{if(Math.abs(e.deltaY)>Math.abs(e.deltaX)){strip.scrollLeft+=e.deltaY;e.preventDefault();}},{passive:false});
  }
  function syncHomeRecord(){
    fetch('data.json?ts='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{
      const team=d.team||d.montana||{};
      const record=team.record||d.record||'—';
      const conf=team.conference_record||team.big_sky_record||d.conference_record||'—';
      const a=document.getElementById('home-montana-record');
      const b=document.getElementById('home-snapshot-record');
      if(a)a.textContent=record;
      if(b)b.textContent=record;
      document.querySelectorAll('.v2-home-next-match small').forEach(el=>{if(el.textContent.trim()==='MONTANA')el.innerHTML='MONTANA<br>'+record;});
      document.querySelectorAll('.ghq-nu-team.is-griz p').forEach(el=>{el.textContent=record+' • '+conf+' BIG SKY';});
    }).catch(()=>{});
  }
  function init(){wireScorebar();syncHomeRecord();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
  setTimeout(wireScorebar,1000);
  setTimeout(wireScorebar,2500);
})();
'''
if js_marker not in js_text:
    js.write_text(js_text + js_patch, encoding='utf-8')

print('Applied scorebar and homepage record hotfix')
