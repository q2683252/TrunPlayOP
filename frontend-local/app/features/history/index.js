import {
  byId,
  buildThumbnailUrl,
  escapeHtml,
  formatDuration,
  historyTimeParts,
} from '../../core/helpers.js';

const statusMap = {
  IN_PROGRESS: { label: '播放中', cls: 'playing' },
  COMPLETED: { label: '已完成', cls: 'completed' },
  STOPPED: { label: '已停止', cls: 'stopped' },
  ERROR: { label: '出错', cls: 'error' },
  PAUSED: { label: '已暂停', cls: 'paused' },
};

const triggerMap = {
  SCHEDULED: '定时',
  SCHEDULE: '定时',
  MANUAL: '手动',
  API: '接口',
};

function statusBadge(value) {
  const status = statusMap[String(value || '').toUpperCase()] || { label: value || '-', cls: 'stopped' };
  return `<span class="tp-history-badge tp-history-badge--${status.cls}"><span class="tp-history-badge-dot"></span>${escapeHtml(status.label)}</span>`;
}

export function registerHistory(app) {
  const listEl = byId('history-list');
  const paginationEl = byId('history-pagination');
  const refreshBtn = byId('btn-refresh-history');
  const clearBtn = byId('btn-clear-history');

  let page = 1;
  const pageSize = 20;

  async function loadHistory(options = {}) {
    if (!listEl || !paginationEl) return [];
    const silent = Boolean(options.silent);
    const requestKey = options.requestKey || 'history:list';

    listEl.innerHTML = '<div class="tp-history-loading">加载中...</div>';

    try {
      const data = await app.api.get(`/history?page=${page}&page_size=${pageSize}`, { requestKey });
      const items = Array.isArray(data?.items) ? data.items : [];
      const total = Number(data?.total || 0);

      app.store.patch({ entities: { history: { items, total, page } } });

      if (!items.length) {
        listEl.innerHTML = '<div class="tp-empty-state"><div class="tp-empty-icon">📜</div><h4>暂无播放历史</h4><p>播放媒体后这里会记录每一次播放结果。</p></div>';
        paginationEl.innerHTML = '';
        return items;
      }

      listEl.innerHTML = items
        .map((item) => {
          const thumb = buildThumbnailUrl(item);
          const time = historyTimeParts(item.actual_start_time || item.created_at);
          const name = item.media_name || item.media_url || '-';
          const played = formatDuration(item.played_duration || 0);
          const totalDuration = Number(item.media_duration || 0) > 0 ? formatDuration(item.media_duration) : '';
          const trigger = triggerMap[String(item.trigger_type || '').toUpperCase()] || item.trigger_type || '-';
          const errorMessage = item.end_status === 'ERROR' && item.error_message
            ? `<div class="tp-history-error">${escapeHtml(item.error_message)}</div>`
            : '';

          return `
            <article class="tp-history-card">
              <div class="tp-history-thumb-wrap">
                <img class="tp-history-thumb" src="${thumb}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="tp-history-thumb-placeholder" style="display:none;"><span>🎬</span></div>
                <div class="tp-history-time-overlay"><span class="tp-history-time-date">${escapeHtml(time.date)}</span><span class="tp-history-time-clock">${escapeHtml(time.time)}</span></div>
              </div>
              <div class="tp-history-body">
                <div class="tp-history-title" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
                <div class="tp-history-meta">
                  <span class="tp-history-meta-item" title="计划">${escapeHtml(item.plan_title || '-')}</span>
                  <span class="tp-history-meta-sep"></span>
                  <span class="tp-history-meta-item" title="设备">${escapeHtml(item.device_name || '-')}</span>
                </div>
                <div class="tp-history-footer">
                  ${statusBadge(item.end_status)}
                  <span class="tp-history-dur">${escapeHtml(totalDuration ? `${played} / ${totalDuration}` : played)}</span>
                  <span class="tp-history-trigger">${escapeHtml(trigger)}</span>
                </div>
                ${errorMessage}
              </div>
            </article>
          `;
        })
        .join('');

      const totalPages = Math.max(1, Math.ceil(total / pageSize));
      paginationEl.innerHTML = '';

      if (page > 1) {
        const prev = document.createElement('button');
        prev.className = 'cbi-button';
        prev.textContent = '上一页';
        prev.addEventListener('click', () => {
          page -= 1;
          loadHistory({ silent: true });
        });
        paginationEl.appendChild(prev);
      }

      const label = document.createElement('span');
      label.className = 'tp-page-indicator';
      label.textContent = `第 ${page} / ${totalPages} 页`;
      paginationEl.appendChild(label);

      if (page < totalPages) {
        const next = document.createElement('button');
        next.className = 'cbi-button';
        next.textContent = '下一页';
        next.addEventListener('click', () => {
          page += 1;
          loadHistory({ silent: true });
        });
        paginationEl.appendChild(next);
      }

      return items;
    } catch (err) {
      if (err?.code === 'ABORTED') return [];
      if (!silent) app.ui.toast('error', err.message || '历史记录加载失败');
      listEl.innerHTML = `<div class="tp-empty-state"><div class="tp-empty-icon">⚠</div><h4>加载失败</h4><p>${escapeHtml(err.message || '请检查网络')}</p></div>`;
      paginationEl.innerHTML = '';
      return [];
    }
  }

  refreshBtn?.addEventListener('click', () => {
    page = 1;
    loadHistory();
  });

  clearBtn?.addEventListener('click', async () => {
    const ok = await app.ui.confirm('清空后无法恢复，确定要清空全部播放历史吗？', {
      title: '清空历史',
      type: 'danger',
      okText: '清空',
    });

    if (!ok) return;

    try {
      await app.api.del('/history');
      app.ui.toast('success', '播放历史已清空');
      page = 1;
      loadHistory({ silent: true });
    } catch (err) {
      app.ui.toast('error', err.message || '清空失败');
    }
  });

  return {
    onEnter(tab) {
      if (tab === 'history') {
        page = 1;
        loadHistory({ silent: true });
      }
    },
    loadHistory,
  };
}
