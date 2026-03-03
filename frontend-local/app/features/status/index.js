import { byId, formatBytes, formatDuration, parseDurationToSeconds } from '../../core/helpers.js';

export function registerStatus(app) {
  const log = app.log.status;
  let timer = null;
  const delays = {
    idle: 5000,
    active: 1000,
  };

  const serviceEl = byId('service-status');
  const playbackEl = byId('playback-status');
  const localIpEl = byId('local-ip');
  const deviceNameEl = byId('device-name');
  const dbSizeEl = byId('db-size');
  const panel = byId('playback-panel');
  const mediaNameEl = byId('media-name');
  const currentTimeEl = byId('current-time');
  const totalTimeEl = byId('total-time');
  const progressFill = byId('progress-bar-fill');
  const volumeSlider = byId('volume-slider');
  const volumeLabel = byId('volume-value');
  const progressContainer = document.querySelector('#playback-panel .progress-container');

  function stopPolling() {
    if (timer) clearTimeout(timer);
    timer = null;
  }

  function schedule(delay) {
    stopPolling();
    timer = setTimeout(() => {
      if (app.router.current() !== 'status') return;
      loadStatus({ silent: true });
    }, delay);
  }

  function renderServiceStatus(data) {
    if (!serviceEl || !localIpEl || !dbSizeEl) return;
    serviceEl.textContent = '运行中';
    serviceEl.className = 'status-badge online';
    localIpEl.textContent = `IP: ${data.local_ip || '-'}`;
    dbSizeEl.textContent = formatBytes(data.db_size);
  }

  function renderServiceOffline() {
    if (!serviceEl || !localIpEl || !dbSizeEl) return;
    serviceEl.textContent = '未连接';
    serviceEl.className = 'status-badge error';
    localIpEl.textContent = 'IP: -';
    dbSizeEl.textContent = '-';
  }

  function renderPlayback(data) {
    if (!playbackEl || !deviceNameEl || !panel) return;

    const status = String(data.status || 'STOPPED').toLowerCase();
    const label = status === 'playing' ? '播放中' : status === 'paused' ? '已暂停' : '已停止';
    playbackEl.textContent = label;
    playbackEl.className = `status-badge ${status === 'playing' ? 'playing' : status === 'paused' ? 'paused' : 'stopped'}`;
    deviceNameEl.textContent = data.device_name || '-';

    const hasMedia = Boolean(data.media_name || data.media_url);
    panel.style.display = hasMedia ? 'block' : 'none';

    if (hasMedia) {
      const position = Number(data.position || 0);
      const duration = Number(data.duration || 0);
      mediaNameEl.textContent = data.media_name || data.media_url || '-';
      currentTimeEl.textContent = formatDuration(position);
      totalTimeEl.textContent = formatDuration(duration);
      progressFill.style.width = duration > 0 ? `${Math.min(100, Math.round((position / duration) * 100))}%` : '0%';

      if (volumeSlider && data.volume != null && !volumeSlider.dataset.dragging) {
        volumeSlider.value = Number(data.volume);
        if (volumeLabel) volumeLabel.textContent = String(data.volume);
      }
    }

    app.store.patch({
      entities: {
        playback: {
          status,
          mediaName: data.media_name || data.media_url || '',
          deviceName: data.device_name || '',
        },
      },
    });

    schedule(['playing', 'paused'].includes(status) ? delays.active : delays.idle);
  }

  function renderPlaybackUnknown() {
    if (!playbackEl || !deviceNameEl || !panel) return;
    playbackEl.textContent = '未知';
    playbackEl.className = 'status-badge error';
    deviceNameEl.textContent = '-';
    panel.style.display = 'none';
    app.store.patch({
      entities: {
        playback: { status: 'unknown', mediaName: '', deviceName: '' },
      },
    });
    schedule(delays.idle);
  }

  async function loadStatus(options = {}) {
    const silent = Boolean(options.silent);
    log('info', 'loadStatus');

    try {
      const system = await app.api.get('/system/status', { requestKey: 'status:system' });
      renderServiceStatus(system);
      app.store.patch({
        entities: {
          status: {
            serviceOnline: true,
            localIp: system.local_ip || '',
            dbSize: system.db_size || 0,
          },
        },
      });
    } catch (err) {
      if (err?.code === 'ABORTED') return;
      renderServiceOffline();
      app.store.patch({
        entities: {
          status: { serviceOnline: false, localIp: '', dbSize: 0 },
        },
      });
      if (!silent) app.ui.toast('error', err.message || '服务状态获取失败');
    }

    try {
      const playback = await app.api.get('/playback/status', { requestKey: 'status:playback' });
      renderPlayback(playback);
    } catch (err) {
      if (err?.code === 'ABORTED') return;
      renderPlaybackUnknown();
      if (!silent) app.ui.toast('warning', err.message || '播放状态获取失败');
    }
  }

  async function callPlaybackAction(action, button) {
    const actionLabel = {
      pause: '暂停',
      resume: '继续',
      stop: '停止',
    };
    app.ui.setButtonBusy(button);
    try {
      await app.api.post(`/playback/${action}`);
      app.ui.toast('success', `已${actionLabel[action] || action}播放`);
      await loadStatus({ silent: true });
    } catch (err) {
      app.ui.toast('error', err.message || '操作失败');
    } finally {
      app.ui.clearButtonBusy(button);
    }
  }

  function bindPlaybackControls() {
    document.querySelectorAll('#playback-panel [data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-action');
        callPlaybackAction(action, btn);
      });
    });

    if (volumeSlider) {
      volumeSlider.addEventListener('input', () => {
        volumeSlider.dataset.dragging = '1';
        if (volumeLabel) volumeLabel.textContent = volumeSlider.value;
      });

      volumeSlider.addEventListener('change', async () => {
        const level = Number(volumeSlider.value || 0);
        try {
          await app.api.post('/playback/volume', { level });
          if (volumeLabel) volumeLabel.textContent = String(level);
        } catch (err) {
          app.ui.toast('error', err.message || '音量设置失败');
          await loadStatus({ silent: true });
        } finally {
          delete volumeSlider.dataset.dragging;
        }
      });
    }

    if (progressContainer) {
      progressContainer.style.cursor = 'pointer';
      progressContainer.addEventListener('click', async (event) => {
        const rect = progressContainer.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        const totalSec = parseDurationToSeconds(totalTimeEl?.textContent || '');
        if (totalSec <= 0) return;

        const position = Math.round(totalSec * ratio);
        try {
          await app.api.post('/playback/seek', { position });
          app.ui.toast('info', `已跳转到 ${formatDuration(position)}`);
          await loadStatus({ silent: true });
        } catch (err) {
          app.ui.toast('error', err.message || '进度跳转失败');
        }
      });
    }
  }

  bindPlaybackControls();

  return {
    onEnter() {
      loadStatus({ silent: true });
    },
    onLeave() {
      stopPolling();
      app.api.abortRequest('status:system');
      app.api.abortRequest('status:playback');
    },
    loadStatus,
  };
}
