import { byId, escapeHtml } from './helpers.js';

function ensureToastContainer() {
  let container = byId('tp-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'tp-toast-container';
    container.className = 'tp-toast-container';
    document.body.appendChild(container);
  }
  return container;
}

function createToastElement(type, message, duration) {
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };
  const el = document.createElement('div');
  el.className = `tp-toast tp-toast-${type || 'info'}`;
  el.innerHTML = `
    <span class="tp-toast-icon">${icons[type] || icons.info}</span>
    <span class="tp-toast-text">${escapeHtml(message || '')}</span>
    <button type="button" class="tp-toast-close" aria-label="关闭">×</button>
    <div class="tp-toast-progress"><div class="tp-toast-progress-bar"></div></div>
  `;

  const closeBtn = el.querySelector('.tp-toast-close');
  const progressBar = el.querySelector('.tp-toast-progress-bar');

  function dismiss() {
    if (el.dataset.dismissed === '1') return;
    el.dataset.dismissed = '1';
    if (el._timeout) clearTimeout(el._timeout);
    el.classList.remove('show');
    el.classList.add('hide');
    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 240);
  }

  closeBtn.addEventListener('click', dismiss);
  el._dismiss = dismiss;

  requestAnimationFrame(() => {
    el.classList.add('show');
    if (progressBar) {
      progressBar.style.transition = `width ${duration}ms linear`;
      requestAnimationFrame(() => {
        progressBar.style.width = '0%';
      });
    }
  });

  el._timeout = setTimeout(dismiss, duration);
  return el;
}

export function createUiFeedback() {
  let confirmResolve = null;
  const modalStack = [];
  const buttonText = new WeakMap();

  function toast(type, message, duration = 3600) {
    const container = ensureToastContainer();
    const el = createToastElement(type, message, duration);
    container.appendChild(el);
    return el;
  }

  function closeConfirm(value) {
    const overlay = byId('tp-confirm');
    if (!overlay) return;
    overlay.classList.remove('show');
    setTimeout(() => {
      overlay.style.display = 'none';
    }, 180);
    if (confirmResolve) {
      confirmResolve(Boolean(value));
      confirmResolve = null;
    }
  }

  function confirm(message, options = {}) {
    const overlay = byId('tp-confirm');
    const titleEl = byId('tp-confirm-title');
    const messageEl = byId('tp-confirm-message');
    const iconEl = byId('tp-confirm-icon');
    const okBtn = byId('tp-confirm-ok');
    const cancelBtn = byId('tp-confirm-cancel');

    if (!overlay || !titleEl || !messageEl || !iconEl || !okBtn || !cancelBtn) {
      return Promise.resolve(window.confirm(message));
    }

    titleEl.textContent = options.title || '确认操作';
    messageEl.textContent = message || '确认继续吗？';
    const type = options.type || 'danger';
    iconEl.className = `tp-confirm-icon tp-confirm-icon-${type}`;
    iconEl.textContent = type === 'warning' ? '⚠' : type === 'info' ? 'ℹ' : '⚠';
    okBtn.textContent = options.okText || '确定';
    okBtn.className = `cbi-button ${type === 'danger' ? 'cbi-button-remove' : 'cbi-button-action'}`;
    cancelBtn.textContent = options.cancelText || '取消';

    overlay.style.display = 'flex';
    requestAnimationFrame(() => overlay.classList.add('show'));

    return new Promise((resolve) => {
      confirmResolve = resolve;
    });
  }

  function openModal(id, triggerElement = null) {
    const modal = byId(id);
    if (!modal) return;
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
    if (!modalStack.includes(modal)) modalStack.push(modal);
    modal._returnFocus = triggerElement || document.activeElement;
    const autoFocus = modal.querySelector('input, select, textarea, button');
    if (autoFocus) setTimeout(() => autoFocus.focus(), 0);
  }

  function closeModal(idOrEl) {
    const modal = typeof idOrEl === 'string' ? byId(idOrEl) : idOrEl;
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    const index = modalStack.indexOf(modal);
    if (index >= 0) modalStack.splice(index, 1);
    if (modal._returnFocus && typeof modal._returnFocus.focus === 'function') {
      modal._returnFocus.focus();
    }
  }

  function closeTopModal() {
    const top = modalStack[modalStack.length - 1];
    if (top) closeModal(top);
  }

  function bindModalHandlers() {
    document.querySelectorAll('[data-dismiss]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-dismiss');
        closeModal(target);
      });
    });

    document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
      backdrop.addEventListener('click', () => {
        const modal = backdrop.closest('.modal');
        if (modal) closeModal(modal);
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        if (byId('tp-confirm')?.style.display === 'flex') {
          closeConfirm(false);
          return;
        }
        closeTopModal();
      }
    });

    const okBtn = byId('tp-confirm-ok');
    const cancelBtn = byId('tp-confirm-cancel');
    const overlay = byId('tp-confirm');
    if (okBtn) okBtn.addEventListener('click', () => closeConfirm(true));
    if (cancelBtn) cancelBtn.addEventListener('click', () => closeConfirm(false));
    if (overlay) {
      overlay.addEventListener('click', (event) => {
        if (event.target === overlay) closeConfirm(false);
      });
    }
  }

  function setButtonBusy(btn, text) {
    if (!btn) return;
    if (!buttonText.has(btn)) buttonText.set(btn, btn.textContent || '');
    btn.disabled = true;
    btn.classList.add('btn-loading');
    if (text) btn.textContent = text;
  }

  function clearButtonBusy(btn, fallbackText = '') {
    if (!btn) return;
    btn.disabled = false;
    btn.classList.remove('btn-loading');
    btn.textContent = fallbackText || buttonText.get(btn) || btn.textContent;
    buttonText.delete(btn);
  }

  function clearFieldError(target) {
    const field = typeof target === 'string' ? byId(target) : target;
    if (!field) return;
    field.classList.remove('tp-input-invalid');
    const container = field.closest('.cbi-value-field') || field.parentElement;
    const existing = container?.querySelector('.tp-field-error');
    if (existing) existing.remove();
  }

  function setFieldError(target, message) {
    const field = typeof target === 'string' ? byId(target) : target;
    if (!field) return;
    clearFieldError(field);
    field.classList.add('tp-input-invalid');
    const container = field.closest('.cbi-value-field') || field.parentElement;
    if (!container) return;
    const errorEl = document.createElement('div');
    errorEl.className = 'tp-field-error';
    errorEl.textContent = message || '输入有误';
    container.appendChild(errorEl);
  }

  function showFormAlert(id, type, message) {
    const el = byId(id);
    if (!el) return;
    el.className = `tp-form-alert ${type || 'warning'}`;
    el.textContent = message || '';
    el.style.display = message ? 'block' : 'none';
  }

  function clearFormAlert(id) {
    showFormAlert(id, '', '');
  }

  return {
    bindModalHandlers,
    toast,
    confirm,
    openModal,
    closeModal,
    closeTopModal,
    setButtonBusy,
    clearButtonBusy,
    setFieldError,
    clearFieldError,
    showFormAlert,
    clearFormAlert,
  };
}
