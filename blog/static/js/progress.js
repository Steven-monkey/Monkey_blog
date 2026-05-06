/* ═══════════════════════════════════════════════════
   阅读进度条
   ═══════════════════════════════════════════════════ */
(function() {
  var bar = document.getElementById('reading-progress');
  if (!bar) return;

  function update() {
    var scrollTop = window.scrollY;
    var docHeight = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = docHeight > 0 ? (scrollTop / docHeight) * 100 + '%' : '0%';
  }

  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update, { passive: true });
})();
