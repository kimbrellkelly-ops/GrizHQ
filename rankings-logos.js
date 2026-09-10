(() => {
  const LOGOS = {
    Montana: 'https://a.espncdn.com/i/teamlogos/ncaa/500/149.png',
    MontanaState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/147.png',
    SouthDakota: 'https://a.espncdn.com/i/teamlogos/ncaa/500/233.png',
    NorthDakota: 'https://a.espncdn.com/i/teamlogos/ncaa/500/155.png',
    Idaho: 'https://a.espncdn.com/i/teamlogos/ncaa/500/70.png',
    UC_Davis: 'https://a.espncdn.com/i/teamlogos/ncaa/500/302.png',
    EasternWashington: 'https://a.espncdn.com/i/teamlogos/ncaa/500/331.png',
    Villanova: 'https://a.espncdn.com/i/teamlogos/ncaa/500/222.png',
    SouthDakotaState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/256.png',
    NorthDakotaState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2449.png',
    IllinoisState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/228.png',
    IncarnateWord: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2916.png',
    TarletonState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2627.png',
    Mercer: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2382.png',
    Richmond: 'https://a.espncdn.com/i/teamlogos/ncaa/500/257.png',
    YoungstownState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2754.png',
    Delaware: 'https://a.espncdn.com/i/teamlogos/ncaa/500/48.png',
    NewHampshire: 'https://a.espncdn.com/i/teamlogos/ncaa/500/160.png',
    CentralArkansas: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2110.png',
    StephenFAustin: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2617.png',
    SoutheastMissouriState: 'https://a.espncdn.com/i/teamlogos/ncaa/500/2546.png',
    MontanaAliases: 'https://a.espncdn.com/i/teamlogos/ncaa/500/149.png'
  };

  const ALIASES = {
    'montana': LOGOS.Montana,
    'montanagrizzlies': LOGOS.Montana,
    'montanagriz': LOGOS.Montana,
    'montanastate': LOGOS.MontanaState,
    'southdakota': LOGOS.SouthDakota,
    'southdakotastate': LOGOS.SouthDakotaState,
    'northdakota': LOGOS.NorthDakota,
    'northdakotastate': LOGOS.NorthDakotaState,
    'idaho': LOGOS.Idaho,
    'ucdavis': LOGOS.UC_Davis,
    'easternwashington': LOGOS.EasternWashington,
    'villanova': LOGOS.Villanova,
    'illinoisstate': LOGOS.IllinoisState,
    'incarnateword': LOGOS.IncarnateWord,
    'tarletonstate': LOGOS.TarletonState,
    'mercer': LOGOS.Mercer,
    'richmond': LOGOS.Richmond,
    'youngstownstate': LOGOS.YoungstownState,
    'delaware': LOGOS.Delaware,
    'newhampshire': LOGOS.NewHampshire,
    'centralarkansas': LOGOS.CentralArkansas,
    'stephenfaustin': LOGOS.StephenFAustin,
    'southeastmissouristate': LOGOS.SoutheastMissouriState
  };

  const normalize = value => String(value || '')
    .toLowerCase()
    .replace(/&amp;/g, '&')
    .replace(/[^a-z0-9]/g, '');

  const logoFor = name => {
    const key = normalize(name);
    return ALIASES[key] || '';
  };

  const cleanName = li => {
    const clone = li.cloneNode(true);
    clone.querySelectorAll('.ghq-ranking-logo, img, svg').forEach(el => el.remove());
    return clone.textContent.replace(/^\s*\d+\s*/, '').replace(/\s+/g, ' ').trim();
  };

  const enhance = list => {
    if (!list) return;
    list.querySelectorAll(':scope > li').forEach(li => {
      const name = cleanName(li);
      const url = logoFor(name);
      if (!url || li.querySelector('.ghq-ranking-logo')) return;
      const img = document.createElement('img');
      img.className = 'ghq-ranking-logo';
      img.src = url;
      img.alt = '';
      img.width = 28;
      img.height = 28;
      img.loading = 'lazy';
      img.decoding = 'async';
      img.addEventListener('error', () => img.remove(), { once: true });
      li.prepend(img);
      li.classList.add('ghq-ranking-logo-ready');
    });
  };

  const start = () => {
    if (!document.getElementById('ghq-ranking-logo-style')) {
      const style = document.createElement('style');
      style.id = 'ghq-ranking-logo-style';
      style.textContent = `
        #coaches-poll > li, #media-poll > li { display:flex; align-items:center; gap:10px; }
        #coaches-poll .ghq-ranking-logo, #media-poll .ghq-ranking-logo { width:28px; height:28px; object-fit:contain; flex:0 0 28px; }
      `;
      document.head.appendChild(style);
    }
    enhance(document.getElementById('coaches-poll'));
    enhance(document.getElementById('media-poll'));
    const observer = new MutationObserver(() => {
      enhance(document.getElementById('coaches-poll'));
      enhance(document.getElementById('media-poll'));
    });
    [document.getElementById('coaches-poll'), document.getElementById('media-poll')]
      .filter(Boolean)
      .forEach(el => observer.observe(el, { childList: true, subtree: true }));
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
