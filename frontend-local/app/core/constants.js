export const apiHost = window.location.hostname || '127.0.0.1';
export const apiProtocol = window.location.protocol || 'http:';

export const API_BASE = `${apiProtocol}//${apiHost}:8088/api/v1`;
export const THUMB_BASE = `${API_BASE}/media/thumbnail`;

export const STORAGE_KEYS = {
  lastTab: 'tp:last_tab',
  onboardingDismissed: 'tp:onboarding_dismissed',
};

export const TABS = ['status', 'study', 'devices', 'smb', 'history'];
