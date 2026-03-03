import {
  byId,
  buildThumbnailUrl,
  escapeHtml,
  formatBytes,
  formatDuration,
  formatDurationText,
  renderSkeletonRows,
} from '../../core/helpers.js';

export function registerStudy(app) {
  const tbody = byId('study-tasks-tbody');
  const addBtn = byId('btn-add-study-task');
  const refreshBtn = byId('btn-refresh-study-tasks');
  const saveBtn = byId('btn-save-study-task');
  const browseBtn = byId('btn-study-browse');

  const modal = byId('modal-study-task');
  const titleEl = byId('modal-study-task-title');
  const idInput = byId('study-task-id');
  const nameInput = byId('study-task-name');
  const selectedFilesEl = byId('study-selected-files');

  // Reused media browser modal (legacy IDs kept for compatibility)
  const browserModal = byId('modal-plan-browser');
  const browserSourceLocalBtn = byId('plan-source-local');
  const browserSourceSmbBtn = byId('plan-source-smb');
  const browserSmbServerSelect = byId('plan-smb-server');
  const browserSmbServerRow = byId('plan-smb-server-row');
  const browserListBody = byId('plan-file-list-body');
  const browserBreadcrumbPath = byId('plan-breadcrumb-path');
  const browserSelectAll = byId('plan-file-select-all');
  const browserSelectedCount = byId('plan-selected-count');
  const browserPreviewImg = byId('plan-preview-image');
  const browserPreviewName = byId('plan-preview-name');

  const expandModal = byId('modal-plan-expand-confirm');
  const expandListBody = byId('plan-expand-confirm-list');
  const expandTitle = byId('plan-expand-confirm-title');

  let studySelectedFiles = [];
  let browserState = {
    source: 'smb',
    serverId: '',
    path: '',
    pathPrefix: '',
    files: [],
    tempSelected: [],
    previewFile: null,
    expandResult: null,
  };

  let createFromPlanContext = null;
  let browseRequestSeq = 0;

  function clearTaskForm() {
    if (idInput) idInput.value = '';
    if (nameInput) nameInput.value = '';
    studySelectedFiles = [];
    createFromPlanContext = null;
    app.ui.clearFieldError(nameInput);
    app.ui.clearFormAlert('study-form-alert');
    renderSelectedFiles();
  }

  function abortBrowserRequests() {
    browseRequestSeq += 1;
    app.api.abortRequest('study:browse-local');
    app.api.abortRequest('study:browse-smb');
    app.api.abortRequest('study:browser-servers');
  }

  function closeFileBrowser() {
    abortBrowserRequests();
    app.ui.closeModal(browserModal);
  }

  function renderSelectedFiles() {
    if (!selectedFilesEl) return;

    if (!studySelectedFiles.length) {
      selectedFilesEl.innerHTML = '<span class="tp-muted">未选择文件，点击「浏览文件」选择</span>';
      return;
    }

    selectedFilesEl.innerHTML = `
      <div class="tp-study-file-list">
        <div class="tp-study-file-list-title">已选 ${studySelectedFiles.length} 个文件：</div>
        ${studySelectedFiles
          .map((file, idx) => {
            const thumb = buildThumbnailUrl(file);
            const duration = Number(file.duration || 0);
            const position = Number(file.last_playback_position || 0);
            const pct = duration > 0 ? Math.min(100, Math.round((position / duration) * 100)) : 0;
            const done = pct >= 100;

            return `
              <div class="tp-study-file-item">
                <img class="tp-thumb-sm" src="${thumb}" alt="预览">
                <div class="tp-study-file-info">
                  <div class="tp-study-file-name" title="${escapeHtml(file.name || '-')}" >${escapeHtml(file.name || '-')}</div>
                  ${
                    duration > 0
                      ? `<div class="tp-study-progress-wrap"><div class="tp-study-progress-bar"><div class="tp-study-progress-fill ${done ? 'complete' : ''}" style="width:${pct}%"></div></div><span class="tp-study-progress-text ${done ? 'complete' : ''}">${pct}%</span></div>`
                      : position > 0
                        ? `<div class="tp-study-progress-wrap"><span class="tp-study-progress-text">已播放 ${formatDuration(position)}</span></div>`
                        : ''
                  }
                </div>
                <button type="button" class="cbi-button cbi-button-remove study-remove-file" data-idx="${idx}">删除</button>
              </div>
            `;
          })
          .join('')}
      </div>
    `;

    selectedFilesEl.querySelectorAll('.study-remove-file').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.getAttribute('data-idx'));
        studySelectedFiles.splice(idx, 1);
        renderSelectedFiles();
      });
    });
  }

  function renderTaskRows(tasks) {
    if (!tbody) return;

    if (!tasks.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="tp-empty-state"><div class="tp-empty-icon">📚</div><h4>暂无学习任务</h4><p>创建学习任务来管理媒体文件和播放进度。</p></div></td></tr>';
      return;
    }

    tbody.innerHTML = tasks
      .map((task) => {
        const mediaCount = Array.isArray(task.media_items) ? task.media_items.length : 0;
        const totalDur = Number(task.total_duration || 0);
        const watchedDur = Number(task.watched_duration || 0);
        const progress = totalDur > 0 ? Math.min(100, Math.round((watchedDur / totalDur) * 100)) : 0;
        const totalText = totalDur === 0 && mediaCount > 0 ? '<span class="tp-muted">计算中...</span>' : formatDurationText(totalDur);

        return `
          <tr>
            <td>${escapeHtml(task.name || '-')}</td>
            <td>${mediaCount}</td>
            <td>${totalText}</td>
            <td>${formatDurationText(watchedDur)}</td>
            <td>
              <div class="plan-progress">
                <div class="plan-progress-bar"><div class="plan-progress-fill" style="width:${progress}%"></div></div>
                <span class="plan-progress-text">${progress}%</span>
              </div>
            </td>
            <td>
              <button type="button" class="cbi-button study-edit" data-id="${escapeHtml(task.id)}">编辑</button>
              <button type="button" class="cbi-button study-reset" data-id="${escapeHtml(task.id)}">重置进度</button>
              <button type="button" class="cbi-button cbi-button-remove study-delete" data-id="${escapeHtml(task.id)}">删除</button>
            </td>
          </tr>
        `;
      })
      .join('');

    tbody.querySelectorAll('.study-edit').forEach((btn) => {
      btn.addEventListener('click', () => openStudyTaskModal(btn.getAttribute('data-id')));
    });

    tbody.querySelectorAll('.study-reset').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const ok = await app.ui.confirm('重置后观看进度将清零，确定要重置吗？', {
          title: '重置进度',
          type: 'warning',
          okText: '重置',
        });
        if (!ok) return;

        app.ui.setButtonBusy(btn);
        try {
          await app.api.post(`/study/tasks/${btn.getAttribute('data-id')}/reset`, {});
          app.ui.toast('success', '进度已重置');
          await loadStudyTasks({ silent: true });
        } catch (err) {
          app.ui.toast('error', err.message || '重置失败');
        } finally {
          app.ui.clearButtonBusy(btn, '重置进度');
        }
      });
    });

    tbody.querySelectorAll('.study-delete').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const ok = await app.ui.confirm('删除后关联计划将不再包含该学习任务，确定要删除吗？', {
          title: '删除学习任务',
          type: 'danger',
          okText: '删除',
        });
        if (!ok) return;

        app.ui.setButtonBusy(btn);
        try {
          await app.api.del(`/study/tasks/${btn.getAttribute('data-id')}`);
          app.ui.toast('success', '学习任务已删除');
          await loadStudyTasks({ silent: true });
          app.bus.emit('study:updated');
        } catch (err) {
          app.ui.toast('error', err.message || '删除失败');
        } finally {
          app.ui.clearButtonBusy(btn, '删除');
        }
      });
    });
  }

  async function loadStudyTasks(options = {}) {
    if (!tbody) return [];
    const silent = Boolean(options.silent);
    const requestKey = options.requestKey || 'study:list';

    renderSkeletonRows(tbody, 6, 3);

    try {
      const list = await app.api.get('/study/tasks', { requestKey });
      const tasks = Array.isArray(list) ? list : [];
      app.store.patch({ entities: { studyTasks: tasks } });
      renderTaskRows(tasks);
      return tasks;
    } catch (err) {
      if (err?.code === 'ABORTED') return [];
      if (!silent) app.ui.toast('error', err.message || '学习任务加载失败');
      tbody.innerHTML = `<tr><td colspan="6"><div class="tp-empty-state"><div class="tp-empty-icon">⚠</div><h4>加载失败</h4><p>${escapeHtml(err.message || '请检查网络')}</p></div></td></tr>`;
      return [];
    }
  }

  async function openStudyTaskModal(taskId = null, options = {}) {
    clearTaskForm();
    if (titleEl) titleEl.textContent = taskId ? '编辑学习任务' : '新建学习任务';
    if (idInput) idInput.value = taskId || '';

    if (options.fromPlan) {
      createFromPlanContext = {
        draft: options.draft || null,
      };
    }

    if (!taskId) {
      app.ui.openModal('modal-study-task', addBtn);
      return;
    }

    try {
      const task = await app.api.get(`/study/tasks/${taskId}`, { requestKey: 'study:detail' });
      if (nameInput) nameInput.value = task.name || '';
      if (Array.isArray(task.media_items) && task.media_items.length) {
        studySelectedFiles = task.media_items.map((item) => ({
          id: item.id,
          name: item.media_name,
          uri: item.media_uri,
          type: 'VIDEO',
          source_type: item.source_type || 'SMB',
          server_id: item.server_id || '',
          size: 0,
          last_modified: 0,
          duration: item.duration || 0,
          last_playback_position: item.last_playback_position || 0,
        }));
      }
      renderSelectedFiles();
      app.ui.openModal('modal-study-task', addBtn);
    } catch (err) {
      app.ui.toast('error', err.message || '加载任务详情失败');
    }
  }

  function resetBrowserSelection() {
    browserState.tempSelected = [];
    if (browserSelectedCount) browserSelectedCount.textContent = '已选择: 0 个文件/文件夹';
    if (browserSelectAll) browserSelectAll.checked = false;
  }

  function setBrowserPreview(file) {
    browserState.previewFile = file || null;
    if (!browserPreviewImg || !browserPreviewName) return;

    if (!browserState.previewFile || !browserState.previewFile.uri) {
      browserPreviewImg.removeAttribute('src');
      browserPreviewName.textContent = '选择文件以预览';
      return;
    }

    browserPreviewImg.src = buildThumbnailUrl(browserState.previewFile);
    browserPreviewName.textContent = browserState.previewFile.name || '-';
  }

  function updateTempSelectionFromDom() {
    browserState.tempSelected = [];
    browserListBody.querySelectorAll('.plan-file-cb:checked').forEach((cb) => {
      browserState.tempSelected.push(JSON.parse(cb.dataset.file));
    });
    if (browserSelectedCount) {
      browserSelectedCount.textContent = `已选择: ${browserState.tempSelected.length} 个文件/文件夹`;
    }
    setBrowserPreview(browserState.tempSelected[browserState.tempSelected.length - 1] || null);
  }

  function renderShares(shareNames) {
    browserListBody.innerHTML = '<tr><td colspan="5" style="padding:8px; font-weight:600;">请选择共享（点击进入）</td></tr>';
    shareNames.forEach((name) => {
      const row = browserListBody.insertRow(-1);
      row.innerHTML = `<td></td><td>📁</td><td><a href="#" class="plan-share-link" data-share="${escapeHtml(name)}">${escapeHtml(name)}</a></td><td>共享</td><td>-</td>`;
    });
    browserListBody.querySelectorAll('.plan-share-link').forEach((link) => {
      link.addEventListener('click', (event) => {
        event.preventDefault();
        browsePath(link.getAttribute('data-share'));
      });
    });
  }

  function renderBreadcrumb(path) {
    if (!browserBreadcrumbPath) return;
    const rootPath = browserState.pathPrefix || '';

    if (!path && !rootPath) {
      browserBreadcrumbPath.innerHTML = '<a href="#" class="plan-bread-root">根目录</a>';
      const root = browserBreadcrumbPath.querySelector('.plan-bread-root');
      if (root) root.addEventListener('click', (event) => event.preventDefault());
      return;
    }

    const displayPath = path || rootPath;
    const parts = displayPath.split('/').filter(Boolean);
    let built = '';
    let html = '<a href="#" class="plan-bread-root">根目录</a>';

    parts.forEach((part) => {
      built += (built ? '/' : '') + part;
      html += ` &gt; <a href="#" class="plan-bread-link" data-path="${escapeHtml(built)}">${escapeHtml(part)}</a>`;
    });

    browserBreadcrumbPath.innerHTML = html;
    browserBreadcrumbPath.querySelectorAll('.plan-bread-root').forEach((el) => {
      el.addEventListener('click', (event) => {
        event.preventDefault();
        browsePath(rootPath);
      });
    });
    browserBreadcrumbPath.querySelectorAll('.plan-bread-link').forEach((el) => {
      el.addEventListener('click', (event) => {
        event.preventDefault();
        browsePath(el.getAttribute('data-path'));
      });
    });
  }

  function renderFileList() {
    browserListBody.innerHTML = '';

    if (!browserState.files.length) {
      browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">此文件夹为空</td></tr>';
      return;
    }

    browserState.files.forEach((file) => {
      const isFolder = file.type === 'FOLDER';
      const row = browserListBody.insertRow(-1);

      const checkboxCell = row.insertCell(0);
      const iconCell = row.insertCell(1);
      const nameCell = row.insertCell(2);
      const typeCell = row.insertCell(3);
      const sizeCell = row.insertCell(4);

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'plan-file-cb';
      checkbox.dataset.file = JSON.stringify(file);
      checkbox.addEventListener('change', updateTempSelectionFromDom);
      checkboxCell.appendChild(checkbox);

      iconCell.textContent = isFolder ? '📁' : (file.type === 'VIDEO' ? '🎬' : file.type === 'AUDIO' ? '🎵' : '🖼️');

      if (isFolder) {
        const link = document.createElement('a');
        link.href = '#';
        link.className = 'tp-browser-link';
        link.textContent = file.name;
        link.addEventListener('click', (event) => {
          event.preventDefault();
          const nextPath = browserState.pathPrefix ? `${browserState.pathPrefix}/${file.name}` : file.path;
          browsePath(nextPath);
        });
        nameCell.appendChild(link);
      } else {
        nameCell.textContent = file.name;
        row.classList.add('tp-selectable-row');
        row.addEventListener('click', (event) => {
          if (event.target.tagName === 'INPUT') return;
          setBrowserPreview(file);
        });
      }

      typeCell.textContent = isFolder ? '文件夹' : (file.type || '');
      sizeCell.textContent = isFolder ? '-' : formatBytes(file.size);
    });
  }

  async function browsePath(path) {
    const requestSeq = ++browseRequestSeq;

    browserState.path = path || '';
    resetBrowserSelection();
    setBrowserPreview(null);
    renderBreadcrumb(browserState.path);
    browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">加载中...</td></tr>';

    if (browserState.source === 'local') {
      try {
        const data = await app.api.get(`/media/local${browserState.path ? `?path=${encodeURIComponent(browserState.path)}` : ''}`, {
          requestKey: 'study:browse-local',
        });
        if (requestSeq !== browseRequestSeq) return;
        browserState.files = Array.isArray(data?.items) ? data.items : [];
        renderFileList();
      } catch (err) {
        if (requestSeq !== browseRequestSeq || err?.code === 'ABORTED') return;
        browserListBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#b42318;">${escapeHtml(err.message || '浏览失败')}</td></tr>`;
      }
      return;
    }

    if (!browserState.serverId) {
      browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">请选择服务器</td></tr>';
      return;
    }

    try {
      const data = await app.api.get(`/smb/servers/${browserState.serverId}/browse?path=${encodeURIComponent(browserState.path)}`, {
        requestKey: 'study:browse-smb',
      });
      if (requestSeq !== browseRequestSeq) return;
      browserState.files = Array.isArray(data?.items) ? data.items : [];
      browserState.pathPrefix = data?.path_prefix || '';
      renderFileList();
    } catch (err) {
      if (requestSeq !== browseRequestSeq || err?.code === 'ABORTED') return;
      if (Array.isArray(err.details?.available_shares) && err.details.available_shares.length) {
        browserState.pathPrefix = '';
        renderShares(err.details.available_shares);
      } else {
        browserListBody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#b42318;">${escapeHtml(err.message || '浏览失败')}</td></tr>`;
      }
    }
  }

  function setSource(source) {
    abortBrowserRequests();
    browserState.source = source;
    browserState.path = '';
    browserState.pathPrefix = '';
    browserState.serverId = '';

    if (browserSmbServerSelect) browserSmbServerSelect.value = '';
    if (browserSmbServerRow) browserSmbServerRow.style.display = source === 'smb' ? '' : 'none';

    browserSourceLocalBtn?.classList.toggle('cbi-button-positive', source === 'local');
    browserSourceSmbBtn?.classList.toggle('cbi-button-positive', source === 'smb');

    resetBrowserSelection();
    setBrowserPreview(null);
    renderBreadcrumb('');

    if (source === 'local') {
      browsePath('');
    } else {
      browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">请选择服务器</td></tr>';
    }
  }

  async function openFileBrowser() {
    abortBrowserRequests();

    browserState = {
      source: 'smb',
      serverId: '',
      path: '',
      pathPrefix: '',
      files: [],
      tempSelected: [],
      previewFile: null,
      expandResult: null,
    };

    if (browserSmbServerSelect) {
      browserSmbServerSelect.innerHTML = '<option value="">选择服务器</option>';
      try {
        const list = await app.api.get('/smb/servers', { requestKey: 'study:browser-servers' });
        browserSmbServerSelect.innerHTML = '<option value="">选择服务器</option>' + (Array.isArray(list) ? list : [])
          .map((server) => `<option value="${escapeHtml(server.id)}">${escapeHtml(server.name || server.host || '-')}</option>`)
          .join('');
      } catch (_) {
        // keep default option
      }
      browserSmbServerSelect.value = '';
    }

    if (browserSmbServerRow) browserSmbServerRow.style.display = '';
    browserSourceLocalBtn?.classList.remove('cbi-button-positive');
    browserSourceSmbBtn?.classList.add('cbi-button-positive');

    browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">请选择来源或服务器</td></tr>';
    if (browserBreadcrumbPath) browserBreadcrumbPath.innerHTML = '-';
    if (browserSelectedCount) browserSelectedCount.textContent = '已选择: 0 个文件/文件夹';
    setBrowserPreview(null);

    app.ui.openModal(browserModal, browseBtn);
  }

  async function addCurrentFolder() {
    if (browserState.source === 'smb' && !browserState.serverId) {
      app.ui.toast('warning', '请先选择一个 SMB 服务器');
      return;
    }

    let items = [];

    if (browserState.source === 'local') {
      if (!browserState.path) {
        app.ui.toast('info', '请先进入需要导入的本地目录');
        return;
      }
      const path = browserState.path.startsWith('/') ? browserState.path : `/${browserState.path}`;
      items = [{ type: 'FOLDER', uri: `file://${path}`, path, id: 'current', name: path.split('/').filter(Boolean).pop() || path }];
    } else {
      const path = browserState.pathPrefix
        ? `${browserState.pathPrefix}${browserState.path ? `/${browserState.path}` : ''}`
        : browserState.path;
      items = [{ type: 'FOLDER', server_id: browserState.serverId, path: browserState.path || '', id: 'current', name: path ? path.split('/').pop() : '根目录' }];
    }

    browserState.tempSelected = items;
    if (browserSelectedCount) browserSelectedCount.textContent = `已选择: ${items.length} 个文件/文件夹`;
    setBrowserPreview(items[items.length - 1] || null);

    await addSelectedFiles();
  }

  async function addSelectedFiles() {
    if (!browserState.tempSelected.length) {
      app.ui.toast('warning', '请至少选择一个文件或文件夹');
      return;
    }

    let body = null;

    if (browserState.source === 'local') {
      body = {
        items: browserState.tempSelected.map((file) => ({ uri: file.uri })),
      };
    } else {
      body = {
        items: browserState.tempSelected.map((file) => {
          let itemPath = file.path != null ? file.path : browserState.path || '';
          if (browserState.pathPrefix) {
            const shareName = browserState.pathPrefix.split('/')[0];
            if (!itemPath) {
              itemPath = browserState.pathPrefix;
            } else if (shareName && !itemPath.startsWith(`${shareName}/`) && itemPath !== shareName) {
              itemPath = `${shareName}/${itemPath}`;
            }
          }
          return { server_id: browserState.serverId, path: itemPath };
        }),
      };
    }

    try {
      const data = await app.api.post('/media/expand', body, { requestKey: 'study:expand' });
      if (!Array.isArray(data?.items) || !data.items.length) {
        app.ui.toast('warning', browserState.source === 'smb' ? '未找到视频文件，请确认共享路径或继续进入子目录。' : '未找到视频文件');
        return;
      }

      browserState.expandResult = data.items;
      if (expandTitle) expandTitle.textContent = `将导入以下 ${data.items.length} 个视频，请确认顺序`;
      if (expandListBody) {
        expandListBody.innerHTML = '';
        data.items.forEach((item, idx) => {
          const row = expandListBody.insertRow(-1);
          row.insertCell(0).textContent = String(idx + 1);
          row.insertCell(1).textContent = item.name || item.uri || '-';
        });
      }

      app.ui.closeModal(browserModal);
      app.ui.openModal(expandModal);
    } catch (err) {
      if (err?.code === 'ABORTED') return;
      app.ui.toast('error', err.message || '文件展开失败');
    }
  }

  function importExpandedFiles() {
    if (!Array.isArray(browserState.expandResult) || !browserState.expandResult.length) return;

    studySelectedFiles = browserState.expandResult.map((item) => {
      const uri = item.source_type === 'LOCAL' ? item.uri : (item.path || item.uri);
      return {
        id: item.id,
        name: item.name,
        uri,
        path: item.path,
        type: item.type || 'VIDEO',
        source_type: item.source_type || 'SMB',
        server_id: item.server_id || '',
        size: item.size || 0,
        last_modified: item.last_modified || 0,
        duration: item.duration || 0,
        last_playback_position: item.last_playback_position || 0,
      };
    });

    browserState.expandResult = null;
    app.ui.closeModal(expandModal);
    renderSelectedFiles();
  }

  function cancelExpandImport() {
    browserState.expandResult = null;
    app.ui.closeModal(expandModal);
    app.ui.openModal(browserModal, browseBtn);
  }

  async function saveStudyTask() {
    const taskId = idInput?.value || '';
    const name = (nameInput?.value || '').trim();

    app.ui.clearFieldError(nameInput);
    app.ui.clearFormAlert('study-form-alert');

    if (!name) {
      app.ui.setFieldError(nameInput, '请输入学习任务名称');
      app.ui.showFormAlert('study-form-alert', 'warning', '请输入学习任务名称。');
      return;
    }

    if (!studySelectedFiles.length) {
      app.ui.showFormAlert('study-form-alert', 'warning', '请至少选择一个媒体文件。');
      return;
    }

    const payload = {
      name,
      media_items: studySelectedFiles.map((file, idx) => ({
        media_uri: file.uri,
        media_name: file.name,
        duration: 0,
        sort_order: idx,
        source_type: file.source_type || 'SMB',
        server_id: file.server_id || null,
      })),
    };

    const method = taskId ? 'put' : 'post';
    const path = taskId ? `/study/tasks/${taskId}` : '/study/tasks';

    app.ui.setButtonBusy(saveBtn, '保存中...');
    try {
      const saved = await app.api[method](path, payload);
      app.ui.toast('success', taskId ? '学习任务已更新' : '学习任务已创建');
      app.ui.closeModal(modal);

      await loadStudyTasks({ silent: true });
      setTimeout(() => loadStudyTasks({ silent: true }), 3000);

      if (!taskId && createFromPlanContext?.draft) {
        app.bus.emit('study:created-for-plan', {
          task: saved,
          draft: createFromPlanContext.draft,
        });
      }
    } catch (err) {
      app.ui.showFormAlert('study-form-alert', 'error', err.message || '保存失败');
    } finally {
      app.ui.clearButtonBusy(saveBtn, '保存');
    }
  }

  addBtn?.addEventListener('click', () => openStudyTaskModal(null));
  refreshBtn?.addEventListener('click', () => loadStudyTasks());
  saveBtn?.addEventListener('click', saveStudyTask);
  browseBtn?.addEventListener('click', openFileBrowser);

  byId('btn-close-plan-browser')?.addEventListener('click', closeFileBrowser);
  byId('btn-cancel-plan-browser')?.addEventListener('click', closeFileBrowser);
  byId('btn-add-plan-files')?.addEventListener('click', addSelectedFiles);
  byId('btn-add-current-folder')?.addEventListener('click', addCurrentFolder);

  byId('btn-plan-expand-confirm')?.addEventListener('click', importExpandedFiles);
  byId('btn-plan-expand-cancel')?.addEventListener('click', cancelExpandImport);

  browserSourceLocalBtn?.addEventListener('click', () => setSource('local'));
  browserSourceSmbBtn?.addEventListener('click', () => setSource('smb'));

  browserSmbServerSelect?.addEventListener('change', () => {
    browserState.serverId = browserSmbServerSelect.value;
    browserState.path = '';
    browserState.pathPrefix = '';
    resetBrowserSelection();
    if (browserState.serverId) {
      browsePath('');
    } else {
      browserListBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#667085;">请选择服务器</td></tr>';
    }
  });

  browserSelectAll?.addEventListener('click', () => {
    const checked = browserSelectAll.checked;
    browserListBody.querySelectorAll('.plan-file-cb').forEach((cb) => {
      cb.checked = checked;
    });
    updateTempSelectionFromDom();
  });

  return {
    onEnter(tab) {
      if (tab === 'study') loadStudyTasks({ silent: true });
    },
    loadStudyTasks,
    openStudyTaskModal,
    startCreateForPlan(payload) {
      const draft = payload?.draft || null;
      app.router.go('study');
      openStudyTaskModal(null, { fromPlan: true, draft });
    },
  };
}
