// GRIZ HQ — Version 1
// Future versions can replace these static sections with automated feeds,
// live scores, player statistics, and a searchable news database.
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    const target = document.querySelector(link.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({behavior:'smooth'});
    }
  });
});
