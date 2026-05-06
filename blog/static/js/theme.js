/* ═══════════════════════════════════════════════════
   Dark mode toggle — 默认暗色，inline in <head> to prevent FOUC
   ═══════════════════════════════════════════════════ */
(function() {
  var STORAGE_KEY = 'blog-theme';
  var DARK = 'dark';
  var LIGHT = 'light';

  function getPreferredTheme() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === DARK || stored === LIGHT) return stored;
    return DARK; // 默认暗色
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  applyTheme(getPreferredTheme());

  document.addEventListener('DOMContentLoaded', function() {
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    toggle.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-theme') || DARK;
      var next = current === DARK ? LIGHT : DARK;
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  });
})();
