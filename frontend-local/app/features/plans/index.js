import { byId, escapeHtml, renderSkeletonRows } from '../../core/helpers.js';

export function registerPlans(app) {
  const log = app.log.plans;
  const tbody = byId('plans-tbody');
  const addBtn = byId('btn-add-plan');
  const refreshBtn = byId('btn-refresh-plans');
  const saveBtn = byId('btn-save-plan');

  const modal = byId('modal-plan');
  const modalTitle = byId('modal-plan-title');
  const planIdInput = byId('plan-id');
  const planTitleInput = byId('plan-title');
  const planStartInput = byId('plan-start-time');
  const planEndInput = byId('plan-end-time');
  const planDeviceSelect = byId('plan-device');
  const planModeSelect = byId('plan-play-mode');
  const planActiveInput = byId('plan-is-active');
  const planTasksBox = byId('plan-study-tasks-list');
  const planAlertId = 'plan-form-alert';

  const playDurationModal = byId('modal-play-duration');

  let playTarget = {
    planId: '',
    button: null,
  };
  let playRequestInFlight = false;
  let lastPlayTriggerAt = 0;
  let playFailureCooldownUntil = 0;
  const planPlayCooldownUntil = new Map();

  function collectRepeatDays() {
    return Array.from(document.querySelectorAll('.day-check:checked')).map((el) => el.value).join(',');
  }

  function applyRepeatDays(repeat) {
    const values = String(repeat || '').split(',').map((item) => item.trim()).filter(Boolean);
    document.querySelectorAll('.day-check').forEach((el) => {
      el.checked = values.includes(el.value);
    });
  }

  function captureDraft() {
    return {
      title: planTitleInput?.value || '',
      start_time: planStartInput?.value || '09:00',
      end_time: planEndInput?.value || '17:00',
      repeat_days: collectRepeatDays(),
      device_id: planDeviceSelect?.value || '',
      is_active: Boolean(planActiveInput?.checked),
      play_mode: planModeSelect?.value || 'SEQUENTIAL',
    };
  }

  function applyDraft(draft = {}) {
    if (planTitleInput) planTitleInput.value = draft.title || '';
    if (planStartInput) planStartInput.value = draft.start_time || '09:00';
    if (planEndInput) planEndInput.value = draft.end_time || '17:00';
    if (planModeSelect) planModeSelect.value = draft.play_mode || 'SEQUENTIAL';
    if (planActiveInput) planActiveInput.checked = draft.is_active !== false;
    applyRepeatDays(draft.repeat_days || '');
  }

  function formatDeviceOptionLabel(device = {}) {
    const name = device.name || device.address || '-';
    const extras = [device.type, device.address].filter(Boolean).join(' / ');
    return extras ? `${name} (${extras})` : name;
  }

  async function fillDeviceSelect(selectedId = '') {
    if (!planDeviceSelect) return;

    const list = await app.api.get('/devices', { requestKey: 'plans:devices' }).catch(() => []);
    const devices = Array.isArray(list) ? list : [];

    const uniq = [];
    const seen = new Set();
    devices.forEach((device) => {
      const id = String(device?.id || '');
      if (!id || seen.has(id)) return;
      seen.add(id);
      uniq.push(device);
    });

    planDeviceSelect.innerHTML = '<option value="">选择设备</option>' + uniq
      .map((device) => `<option value="${escapeHtml(device.id)}">${escapeHtml(formatDeviceOptionLabel(device))}</option>`)
      .join('');

    planDeviceSelect.value = selectedId || '';
  }

  function renderStudyTaskChecks(tasks, selectedIds = []) {
    if (!planTasksBox) return;

    if (!Array.isArray(tasks) || tasks.length === 0) {
      planTasksBox.innerHTML = `
        <div class="tp-inline-empty">
          <p>暂无学习任务，请先创建一个学习任务后再创建计划。</p>
          <button type="button" class="cbi-button cbi-button-action" id="btn-plan-create-study">立即创建学习任务</button>
        </div>
      `;
      const createBtn = byId('btn-plan-create-study');
      if (createBtn) {
        createBtn.addEventListener('click', () => {
          app.bus.emit('flow:create-study-for-plan', { draft: captureDraft() });
          app.ui.closeModal('modal-plan');
        });
      }
      return;
    }

    planTasksBox.innerHTML = tasks
      .map((task) => {
        const checked = selectedIds.includes(task.id) ? 'checked' : '';
        const mediaCount = Array.isArray(task.media_items) ? task.media_items.length : (task.media_count || 0);
        return `
          <label class="tp-check-row">
            <input type="checkbox" class="plan-study-task-check" value="${escapeHtml(task.id)}" ${checked}>
            <span>${escapeHtml(task.name)} <em>(${mediaCount} 个媒体)</em></span>
          </label>
        `;
      })
      .join('');
  }

  function resetPlanForm() {
    planIdInput.value = '';
    modalTitle.textContent = '新建计划';
    applyDraft({
      title: '',
      start_time: '09:00',
      end_time: '17:00',
      repeat_days: '',
      device_id: '',
      is_active: true,
      play_mode: 'SEQUENTIAL',
    });
    app.ui.clearFieldError(planTitleInput);
    app.ui.clearFormAlert(planAlertId);
  }

  async function openPlanModal(planId = null, options = {}) {
    resetPlanForm();

    if (planId) {
      planIdInput.value = planId;
      modalTitle.textContent = '编辑计划';
    }

    const [studyTasks, planDetail] = await Promise.all([
      app.api.get('/study/tasks', { requestKey: 'plans:studyTasks' }).catch(() => []),
      planId ? app.api.get(`/plans/${planId}`, { requestKey: 'plans:detail' }).catch(() => null) : Promise.resolve(null),
      fillDeviceSelect(options?.draft?.device_id || (planDetail?.device_id || '')),
    ]);

    const detail = planDetail || null;
    const linkedIds = detail?.study_tasks?.map((task) => task.id) || [];
    const preselect = options.preselectTaskIds || [];

    if (detail) {
      applyDraft({
        title: detail.title || '',
        start_time: String(detail.start_time || '09:00').slice(0, 5),
        end_time: String(detail.end_time || '17:00').slice(0, 5),
        repeat_days: detail.repeat_days || '',
        device_id: detail.device_id || '',
        is_active: detail.is_active !== false,
        play_mode: detail.play_mode || 'SEQUENTIAL',
      });
    }

    if (options.draft) {
      applyDraft(options.draft);
    }

    const selectedIds = Array.from(new Set([...(linkedIds || []), ...(preselect || [])]));
    renderStudyTaskChecks(Array.isArray(studyTasks) ? studyTasks : [], selectedIds);

    app.ui.openModal('modal-plan', addBtn);
  }

  async function requestPlanPlay(planId, durationSeconds) {
    let attempts = 0;
    while (attempts < 2) {
      try {
        await app.api.post('/playback/play', {
          plan_id: planId,
          duration: Number(durationSeconds || 0),
        }, {
          requestKey: 'plans:play',
          timeoutMs: 30000,
          logError: false,
        });
        return;
      } catch (err) {
        const msg = String(err?.message || '').toLowerCase();
        const isDbLocked = msg.includes('database is locked');
        if (!isDbLocked || attempts >= 1) throw err;
        await new Promise((resolve) => setTimeout(resolve, 600));
      }
      attempts += 1;
    }
  }

  function updateDeviceOnlineState(deviceId, isOnline) {
    if (!deviceId || typeof isOnline !== 'boolean') return;

    const devices = app.store.getState().entities.devices || [];
    if (!Array.isArray(devices) || devices.length === 0) return;

    let changed = false;
    const nextDevices = devices.map((item) => {
      if (item?.id !== deviceId) return item;
      if (Boolean(item.is_online) === Boolean(isOnline)) return item;
      changed = true;
      return { ...item, is_online: Boolean(isOnline) };
    });

    if (changed) app.store.patch({ entities: { devices: nextDevices } });
  }

  async function probeDeviceOnline(deviceId, fallbackOnline) {
    try {
      const status = await app.api.get(`/devices/${encodeURIComponent(deviceId)}/status`, {
        requestKey: `plans:device-status:${deviceId}`,
        timeoutMs: 9000,
        logError: false,
      });

      const isOnline = typeof status?.is_online === 'boolean'
        ? status.is_online
        : Boolean(fallbackOnline);
      updateDeviceOnlineState(deviceId, isOnline);
      return Boolean(isOnline);
    } catch (err) {
      if (err?.status === 404) return Boolean(fallbackOnline);
      return false;
    }
  }

  async function isPlanDeviceReady(planId) {
    const plans = app.store.getState().entities.plans || [];
    const targetPlan = plans.find((item) => item.id === planId);
    const deviceId = String(targetPlan?.device_id || '').trim();

    if (!deviceId) return true;

    let devices = await app.api.get('/devices', { requestKey: 'plans:play-devices', logError: false }).catch(() => null);
    if (Array.isArray(devices)) {
      app.store.patch({ entities: { devices } });
    } else {
      devices = app.store.getState().entities.devices || [];
    }

    if (!Array.isArray(devices)) return true;

    const targetDevice = devices.find((item) => item.id === deviceId);
    if (!targetDevice) return true;

    const cachedOnline = Boolean(targetDevice.is_online);
    if (!cachedOnline) return false;

    return probeDeviceOnline(deviceId, cachedOnline);
  }


  async function startPlanPlay(planId, durationSeconds, button) {
    if (!planId) return;
    if (playRequestInFlight) {
      app.ui.toast('info', '正在发起播放，请稍候...');
      return;
    }

    const now = Date.now();
    if (now < playFailureCooldownUntil) {
      app.ui.toast('warning', '设备尚未恢复，请先扫描设备后再试');
      return;
    }

    const planCooldownUntil = Number(planPlayCooldownUntil.get(planId) || 0);
    if (now < planCooldownUntil) {
      app.ui.toast('warning', '该计划设备尚未恢复，请先扫描设备后再试');
      return;
    }

    if (now - lastPlayTriggerAt < 2000) {
      app.ui.toast('info', '操作过于频繁，请稍候再试');
      return;
    }
    lastPlayTriggerAt = now;

    playRequestInFlight = true;
    if (button) app.ui.setButtonBusy(button, '播放中...');

    try {
      const ready = await isPlanDeviceReady(planId);
      if (!ready) {
        app.ui.toast('warning', '目标设备离线，请先扫描并确认设备在线');
        return;
      }

      await requestPlanPlay(planId, durationSeconds);
      playFailureCooldownUntil = 0;
      planPlayCooldownUntil.delete(planId);
      app.ui.toast('success', '已开始播放');
      app.features.status?.loadStatus({ silent: true });
    } catch (err) {
      const msg = String(err?.message || '').toLowerCase();
      const isDeviceUnavailable = err?.status === 503 || msg.includes('投屏设备不可用') || msg.includes('离线') || msg.includes('connection refused') || msg.includes('service unavailable');
      if (isDeviceUnavailable) {
        const cooldownUntil = Date.now() + 90 * 1000;
        playFailureCooldownUntil = cooldownUntil;
        planPlayCooldownUntil.set(planId, cooldownUntil);
        app.ui.toast('warning', '设备当前不可用，请先扫描设备后再试');
      } else if (err?.code !== 'ABORTED') {
        app.ui.toast('error', err.message || '播放失败');
      }
    } finally {
      playRequestInFlight = false;
      if (button) app.ui.clearButtonBusy(button, '播放');
    }
  }

  function openPlayDuration(planId, trigger) {
    playTarget = { planId, button: trigger || null };
    app.ui.openModal('modal-play-duration', trigger);
  }

  function openPlayDurationForFirstPlan() {
    const plans = app.store.getState().entities.plans || [];
    if (!plans.length) {
      app.ui.toast('warning', '请先创建至少一个计划');
      return;
    }
    openPlayDuration(plans[0].id, null);
  }

  function bindPlayDurationModal() {
    if (!playDurationModal) return;
    playDurationModal.querySelectorAll('[data-duration]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const duration = Number(btn.getAttribute('data-duration') || 0);
        const { planId, button } = playTarget;
        app.ui.closeModal(playDurationModal);
        playTarget = { planId: '', button: null };
        await startPlanPlay(planId, duration, button);
      });
    });
  }

  async function loadPlans(options = {}) {
    if (!tbody) return [];
    const silent = Boolean(options.silent);
    const requestKey = options.requestKey || 'plans:list';

    renderSkeletonRows(tbody, 7, 3);

    try {
      const list = await app.api.get('/plans', { requestKey });
      const plans = Array.isArray(list) ? list : [];
      app.store.patch({ entities: { plans } });

      if (plans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7"><div class="tp-empty-state"><div class="tp-empty-icon">📋</div><h4>暂无计划</h4><p>创建一个播放计划来开始定时投屏。</p></div></td></tr>';
        return plans;
      }

      tbody.innerHTML = plans
        .map((plan) => {
          const active = Boolean(plan.is_active);
          const studyTasks = Array.isArray(plan.study_tasks) ? plan.study_tasks : [];
          const linkedText = studyTasks.length
            ? studyTasks.map((task) => escapeHtml(task.name)).join('、')
            : '<span class="tp-muted">未关联</span>';

          const progress = Math.max(0, Math.min(100, Math.round(Number(plan.progress_percent || 0))));

          return `
            <tr>
              <td>${escapeHtml(plan.title || '-')}</td>
              <td>${linkedText}</td>
              <td>${escapeHtml(plan.start_time || '-')}</td>
              <td>${escapeHtml(plan.repeat_days || '-')}</td>
              <td>
                <div class="plan-progress">
                  <div class="plan-progress-bar"><div class="plan-progress-fill" style="width:${progress}%"></div></div>
                  <span class="plan-progress-text">${progress}%</span>
                </div>
              </td>
              <td><span class="status-badge ${active ? 'active' : 'inactive'}">${active ? '启用' : '停用'}</span></td>
              <td>
                <button type="button" class="cbi-button cbi-button-action plan-play" data-id="${escapeHtml(plan.id)}">播放</button>
                <button type="button" class="cbi-button plan-edit" data-id="${escapeHtml(plan.id)}">编辑</button>
                <button type="button" class="cbi-button plan-toggle" data-id="${escapeHtml(plan.id)}" data-active="${active ? '1' : '0'}">${active ? '停用' : '启用'}</button>
                <button type="button" class="cbi-button cbi-button-remove plan-delete" data-id="${escapeHtml(plan.id)}">删除</button>
              </td>
            </tr>
          `;
        })
        .join('');

      tbody.querySelectorAll('.plan-play').forEach((btn) => {
        btn.addEventListener('click', () => openPlayDuration(btn.getAttribute('data-id'), btn));
      });

      tbody.querySelectorAll('.plan-edit').forEach((btn) => {
        btn.addEventListener('click', () => openPlanModal(btn.getAttribute('data-id')));
      });

      tbody.querySelectorAll('.plan-toggle').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          const active = btn.getAttribute('data-active') === '1';
          app.ui.setButtonBusy(btn);
          try {
            await app.api.post(`/plans/${id}/${active ? 'deactivate' : 'activate'}`);
            app.ui.toast('success', active ? '计划已停用' : '计划已启用');
            await loadPlans({ silent: true });
          } catch (err) {
            app.ui.toast('error', err.message || '操作失败');
          } finally {
            app.ui.clearButtonBusy(btn, active ? '停用' : '启用');
          }
        });
      });

      tbody.querySelectorAll('.plan-delete').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const ok = await app.ui.confirm('删除后无法恢复，确定要删除该计划吗？', {
            title: '删除计划',
            type: 'danger',
            okText: '删除',
          });
          if (!ok) return;

          app.ui.setButtonBusy(btn);
          try {
            await app.api.del(`/plans/${btn.getAttribute('data-id')}`);
            app.ui.toast('success', '计划已删除');
            await loadPlans({ silent: true });
          } catch (err) {
            app.ui.toast('error', err.message || '删除失败');
          } finally {
            app.ui.clearButtonBusy(btn, '删除');
          }
        });
      });

      return plans;
    } catch (err) {
      if (err?.code === 'ABORTED') return [];
      if (!silent) app.ui.toast('error', err.message || '加载计划失败');
      tbody.innerHTML = `<tr><td colspan="7"><div class="tp-empty-state"><div class="tp-empty-icon">⚠</div><h4>加载失败</h4><p>${escapeHtml(err.message || '请检查网络连接')}</p></div></td></tr>`;
      return [];
    }
  }

  async function savePlan() {
    const planId = planIdInput?.value || '';
    const title = (planTitleInput?.value || '').trim();
    const selectedTaskIds = Array.from(document.querySelectorAll('.plan-study-task-check:checked')).map((el) => el.value);

    app.ui.clearFieldError(planTitleInput);
    app.ui.clearFormAlert(planAlertId);

    if (!title) {
      app.ui.setFieldError(planTitleInput, '请输入计划标题');
      app.ui.showFormAlert(planAlertId, 'warning', '请补充计划标题后再保存。');
      return;
    }

    if (selectedTaskIds.length === 0) {
      app.ui.showFormAlert(planAlertId, 'warning', '请至少关联一个学习任务。');
      return;
    }

    const payload = {
      title,
      start_time: planStartInput?.value || '09:00',
      end_time: planEndInput?.value || '17:00',
      repeat_days: collectRepeatDays(),
      device_id: planDeviceSelect?.value || null,
      is_active: Boolean(planActiveInput?.checked),
      play_mode: planModeSelect?.value || 'SEQUENTIAL',
      study_task_ids: selectedTaskIds,
    };

    app.ui.setButtonBusy(saveBtn, '保存中...');

    try {
      const method = planId ? 'put' : 'post';
      const path = planId ? `/plans/${planId}` : '/plans';
      const plan = await app.api[method](path, payload);

      if (!plan?.id) throw new Error('计划保存失败');

      await app.api.post(`/plans/${plan.id}/link-study-tasks`, {
        study_task_ids: selectedTaskIds,
      });

      app.ui.toast('success', planId ? '计划已更新' : '计划已创建');
      app.ui.closeModal(modal);
      await loadPlans({ silent: true });
    } catch (err) {
      app.ui.showFormAlert(planAlertId, 'error', err.message || '保存失败');
    } finally {
      app.ui.clearButtonBusy(saveBtn, '保存');
    }
  }

  addBtn?.addEventListener('click', (event) => openPlanModal(null, { trigger: event.currentTarget }));
  refreshBtn?.addEventListener('click', () => loadPlans());
  saveBtn?.addEventListener('click', savePlan);

  bindPlayDurationModal();

  return {
    onEnter(tab) {
      if (tab === 'status') loadPlans({ silent: true });
    },
    loadPlans,
    openPlanModal,
    openPlayDurationForFirstPlan,
  };
}
