import { STORAGE_KEYS } from '../../core/constants.js';
import { byId, escapeHtml } from '../../core/helpers.js';

export function registerOnboarding(app) {
  const panel = byId('onboarding-panel');
  const stepsEl = byId('onboarding-steps');
  const dismissBtn = byId('onboarding-dismiss');
  const summaryEl = byId('onboarding-summary');

  if (!panel || !stepsEl || !dismissBtn || !summaryEl) {
    return { render() {} };
  }

  function getSteps(state) {
    const smbReady = (state.entities.smbServers || []).length > 0;
    const deviceReady = (state.entities.devices || []).length > 0;
    const studyReady = (state.entities.studyTasks || []).length > 0;
    const planReady = (state.entities.plans || []).length > 0;
    const playback = state.entities.playback || {};
    const played = ['playing', 'paused'].includes(String(playback.status || '').toLowerCase());

    return [
      {
        key: 'smb',
        title: '配置 SMB 存储',
        description: '连接 NAS 或共享目录用于媒体浏览。',
        done: smbReady,
        action: 'open-smb',
        cta: '去添加 SMB',
      },
      {
        key: 'device',
        title: '发现播放设备',
        description: '扫描并确认投屏设备在线。',
        done: deviceReady,
        action: 'open-devices',
        cta: '去扫描设备',
      },
      {
        key: 'study',
        title: '创建学习任务',
        description: '把媒体文件组织成可学习的任务。',
        done: studyReady,
        action: 'open-study',
        cta: '新建学习任务',
      },
      {
        key: 'plan',
        title: '创建播放计划',
        description: '设定时段、重复日和目标设备。',
        done: planReady,
        action: 'open-plan',
        cta: '新建播放计划',
      },
      {
        key: 'play',
        title: '开始首次播放',
        description: '验证闭环是否完成并进入日常使用。',
        done: played,
        action: 'play-first-plan',
        cta: '开始播放',
      },
    ];
  }

  function handleAction(action) {
    if (action === 'open-smb') {
      app.router.go('smb');
      app.features.smb?.openCreateModal?.();
      return;
    }
    if (action === 'open-devices') {
      app.router.go('devices');
      return;
    }
    if (action === 'open-study') {
      app.router.go('study');
      app.features.study?.openStudyTaskModal?.(null);
      return;
    }
    if (action === 'open-plan') {
      app.router.go('status');
      app.features.plans?.openPlanModal?.(null);
      return;
    }
    if (action === 'play-first-plan') {
      app.router.go('status');
      app.features.plans?.openPlayDurationForFirstPlan?.();
    }
  }

  function bindActions() {
    stepsEl.querySelectorAll('[data-onboarding-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.getAttribute('data-onboarding-action');
        handleAction(action);
      });
    });
  }

  function render(state = app.store.getState()) {
    const steps = getSteps(state);
    const completed = steps.filter((step) => step.done).length;
    const allDone = completed === steps.length;

    if (state.ui.onboardingDismissed && allDone) {
      panel.style.display = 'none';
      return;
    }

    panel.style.display = 'block';
    panel.classList.toggle('all-done', allDone);

    summaryEl.innerHTML = allDone
      ? '流程已全部打通，可以直接在下方管理计划与播放。'
      : `已完成 <strong>${completed}/${steps.length}</strong> 步，继续完成即可形成可复用闭环。`;

    stepsEl.innerHTML = steps
      .map(
        (step, index) => `
          <li class="tp-onboarding-step ${step.done ? 'done' : ''}">
            <div class="tp-onboarding-step-index">${index + 1}</div>
            <div class="tp-onboarding-step-body">
              <div class="tp-onboarding-step-title">${escapeHtml(step.title)}</div>
              <div class="tp-onboarding-step-desc">${escapeHtml(step.description)}</div>
            </div>
            <div class="tp-onboarding-step-actions">
              ${
                step.done
                  ? '<span class="tp-step-done">已完成</span>'
                  : `<button type="button" class="cbi-button cbi-button-action" data-onboarding-action="${step.action}">${escapeHtml(step.cta)}</button>`
              }
            </div>
          </li>
        `,
      )
      .join('');

    bindActions();
  }

  dismissBtn.addEventListener('click', () => {
    localStorage.setItem(STORAGE_KEYS.onboardingDismissed, '1');
    app.store.patch({ ui: { onboardingDismissed: true } });
    panel.style.display = 'none';
  });

  app.store.subscribe((state) => {
    render(state);
  });

  return {
    render,
  };
}
