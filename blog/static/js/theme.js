/* ═══════════════════════════════════════════════════
   Theme toggle — 默认暗色，sidebar 按钮切换
   ═══════════════════════════════════════════════════ */
(function() {
  var STORAGE_KEY = 'blog-theme';
  var DARK = 'dark';
  var LIGHT = 'light';

  function getTheme() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (stored === DARK || stored === LIGHT) return stored;
    return DARK;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  applyTheme(getTheme());

  document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('themeToggle');
    if (!btn) return;

    function updateLabel() {
      var current = document.documentElement.getAttribute('data-theme') || DARK;
      btn.innerHTML = current === DARK ? '<span>☀️</span> <span>浅色模式</span>' : '<span>🌙</span> <span>深色模式</span>';
    }

    updateLabel();
    btn.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-theme') || DARK;
      var next = current === DARK ? LIGHT : DARK;
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
      updateLabel();
    });
  });
})();
