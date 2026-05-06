/* ═══════════════════════════════════════════════════
   Dark mode toggle — inline in <head> to prevent FOUC
   ═══════════════════════════════════════════════════ */
(function() {
  var STORAGE_KEY = 'blog-theme';
  var DARK = 'dark';
  var LIGHT = 'light';

  function getPreferredTheme() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === DARK || stored === LIGHT) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  applyTheme(getPreferredTheme());

  document.addEventListener('DOMContentLoaded', function() {
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;

    toggle.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-theme') || LIGHT;
      var next = current === DARK ? LIGHT : DARK;
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  });
})();
