// ============================================================
// PAGE TRANSITION MANAGER
// Fade-out on nav click before navigating
// ============================================================

(function () {
  function handleNavClick(e) {
    const link = e.currentTarget;
    const href = link.getAttribute('href');

    // Only intercept same-origin local page links
    if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto')) return;

    e.preventDefault();
    document.body.classList.add('page-exit');

    setTimeout(() => {
      window.location.href = href;
    }, 220);
  }

  function attachTransitions() {
    const navLinks = document.querySelectorAll('nav a[href]');
    navLinks.forEach(link => link.addEventListener('click', handleNavClick));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachTransitions);
  } else {
    attachTransitions();
  }
})();
