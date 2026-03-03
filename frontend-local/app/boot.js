import { API_BASE, STORAGE_KEYS } from './core/constants.js';
import { createLoggers } from './core/logger.js';
import { createApiClient } from './core/api-client.js';
import { createStore } from './core/store.js';
import { createRouter } from './core/router.js';
import { createUiFeedback } from './core/ui-feedback.js';
import { createEventBus } from './core/event-bus.js';

import { registerStatus } from './features/status/index.js';
import { registerPlans } from './features/plans/index.js';
import { registerStudy } from './features/study/index.js';
import { registerDevices } from './features/devices/index.js';
import { registerSmb } from './features/smb/index.js';
import { registerHistory } from './features/history/index.js';
import { registerOnboarding } from './features/onboarding/index.js';

const log = createLoggers();
const api = createApiClient({ baseUrl: API_BASE, timeoutMs: 8000, log: log.api });
const ui = createUiFeedback();
const bus = createEventBus();

const store = createStore({
  entities: {
    status: {
      serviceOnline: false,
      localIp: '',
      dbSize: 0,
    },
    playback: {
      status: 'unknown',
      mediaName: '',
      deviceName: '',
    },
    plans: [],
    devices: [],
    smbServers: [],
    studyTasks: [],
    history: {
      items: [],
      total: 0,
      page: 1,
    },
  },
  ui: {
    currentTab: 'status',
    onboardingDismissed: localStorage.getItem(STORAGE_KEYS.onboardingDismissed) === '1',
  },
});

const app = {
  api,
  bus,
  log,
  store,
  ui,
  router: null,
  features: {},
};

ui.bindModalHandlers();

app.features.status = registerStatus(app);
app.features.plans = registerPlans(app);
app.features.study = registerStudy(app);
app.features.devices = registerDevices(app);
app.features.smb = registerSmb(app);
app.features.history = registerHistory(app);
app.features.onboarding = registerOnboarding(app);

let previousTab = null;

app.router = createRouter({
  defaultTab: 'status',
  onChange(tab) {
    store.patch({ ui: { currentTab: tab } });

    if (previousTab && app.features[previousTab]?.onLeave) {
      app.features[previousTab].onLeave(previousTab);
    }

    Object.keys(app.features).forEach((name) => {
      if (app.features[name]?.onEnter && (name === tab || (name === 'plans' && tab === 'status'))) {
        app.features[name].onEnter(tab);
      }
    });

    previousTab = tab;
  },
});

bus.on('flow:create-study-for-plan', (payload) => {
  app.features.study?.startCreateForPlan(payload || {});
});

bus.on('study:created-for-plan', (payload) => {
  if (!payload?.task?.id) return;
  app.router.go('status');
  app.features.plans?.openPlanModal?.(null, {
    draft: payload.draft || null,
    preselectTaskIds: [payload.task.id],
  });
  ui.toast('success', '学习任务已创建，已自动回填到计划表单');
});

async function warmupDataForOnboarding() {
  try {
    await Promise.all([
      app.features.smb.loadSmb({ silent: true }),
      app.features.devices.loadDevices({ silent: true }),
      app.features.study.loadStudyTasks({ silent: true }),
      app.features.plans.loadPlans({ silent: true }),
      app.features.status.loadStatus({ silent: true }),
    ]);
  } catch (err) {
    log.ui('warn', 'warmup failed', err);
  }
}

window.trunplayTestDiscover = function trunplayTestDiscover() {
  return api.post('/devices/discover', {});
};

app.router.init();
warmupDataForOnboarding();
