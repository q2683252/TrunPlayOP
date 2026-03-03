import { THUMB_BASE } from './constants.js';

export function byId(id) {
  return document.getElementById(id);
}

export function escapeHtml(value) {
  if (value == null) return '';
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}

export function formatBytes(size) {
  if (size === undefined || size === null || Number.isNaN(Number(size))) return '-';
  const value = Number(size);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(2)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return '-';
  const sec = Math.max(0, Math.floor(Number(seconds)));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function formatDurationText(totalSeconds) {
  if (!totalSeconds || totalSeconds <= 0) return '-';
  const sec = Math.floor(totalSeconds);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function formatDateTime(value) {
  if (!value) return '-';
  const date = new Date(typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : value);
  return date.toLocaleString('zh-CN');
}

export function historyTimeParts(value) {
  if (!value) return { date: '-', time: '' };
  const date = new Date(typeof value === 'number' ? (value < 1e12 ? value * 1000 : value) : value);
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const mi = String(date.getMinutes()).padStart(2, '0');
  return { date: `${mm}-${dd}`, time: `${hh}:${mi}` };
}

export function parseDurationToSeconds(text) {
  if (!text) return 0;
  const parts = String(text).split(':').map(Number).filter((n) => !Number.isNaN(n));
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

export function buildThumbnailUrl(file) {
  if (!file) return '';
  let uri = file.uri || file.media_uri || file.media_url || file.path || '';
  if (!uri || String(uri).startsWith('study_task://')) return '';
  const sourceType = String(file.source_type || '').toUpperCase();
  if (!String(uri).startsWith('file://') && !String(uri).startsWith('smb://')) {
    if (sourceType === 'SMB') {
      uri = `smb://server/${String(uri).replace(/^\/+/, '')}`;
    } else {
      const path = String(uri).startsWith('/') ? String(uri) : `/${uri}`;
      uri = `file://${path}`;
    }
  }
  const query = new URLSearchParams();
  query.set('uri', uri);
  if (file.server_id) query.set('server_id', file.server_id);
  if (file.source_type) query.set('source_type', file.source_type);
  if (file.path) query.set('path', file.path);
  if (file.last_modified) query.set('last_modified', String(file.last_modified));
  return `${THUMB_BASE}?${query.toString()}`;
}

export function renderSkeletonRows(tbody, cols, rows = 3) {
  if (!tbody) return;
  let html = '';
  for (let i = 0; i < rows; i += 1) {
    html += '<tr>';
    for (let j = 0; j < cols; j += 1) {
      const width = 36 + Math.round(Math.random() * 42);
      html += `<td><span class="tp-skeleton tp-skeleton-text" style="width:${width}%"></span></td>`;
    }
    html += '</tr>';
  }
  tbody.innerHTML = html;
}

export function classNames(...list) {
  return list.filter(Boolean).join(' ');
}
