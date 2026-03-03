import { TABS, STORAGE_KEYS } from './constants.js';

export function createRouter({ defaultTab = 'status', onChange }) {
  function normalizeTab(value) {
    const tab = String(value || '').replace('#', '');
    return TABS.includes(tab) ? tab : defaultTab;
  }

  function applyView(tab) {
    document.querySelectorAll('.nav-btn').forEach((btn) => {
      const active = btn.getAttribute('data-page') === tab;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-current', active ? 'page' : 'false');
    });
    document.querySelectorAll('.page').forEach((page) => {
      const active = page.id === `page-${tab}`;
      page.classList.toggle('active', active);
      page.hidden = !active;
    });
  }

  function setActiveTab(tab, pushHash = true) {
    const normalized = normalizeTab(tab);
    applyView(normalized);
    localStorage.setItem(STORAGE_KEYS.lastTab, normalized);
    if (pushHash && window.location.hash !== `#${normalized}`) {
      window.location.hash = normalized;
    }
    if (typeof onChange === 'function') onChange(normalized);
  }

  function getInitialTab() {
    const hashTab = normalizeTab(window.location.hash);
    if (window.location.hash && TABS.includes(hashTab)) return hashTab;
    return normalizeTab(localStorage.getItem(STORAGE_KEYS.lastTab) || defaultTab);
  }

  function init() {
    document.querySelectorAll('.nav-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-page');
        setActiveTab(tab, true);
      });
    });

    window.addEventListener('hashchange', () => {
      setActiveTab(window.location.hash, false);
    });

    setActiveTab(getInitialTab(), true);
  }

  return {
    init,
    go(tab) {
      setActiveTab(tab, true);
    },
    current() {
      return normalizeTab(window.location.hash || localStorage.getItem(STORAGE_KEYS.lastTab) || defaultTab);
    },
  };
}
