import { byId, escapeHtml, renderSkeletonRows } from '../../core/helpers.js';

export function registerSmb(app) {
  const tbody = byId('smb-tbody');
  const scanBtn = byId('btn-scan-smb');
  const addBtn = byId('btn-add-smb');
  const refreshBtn = byId('btn-refresh-smb');
  const saveBtn = byId('btn-save-smb');
  const testBtn = byId('btn-test-smb');

  const scanResult = byId('smb-scan-result');
  const scanMessage = byId('smb-scan-message');
  const scanTbody = byId('smb-scan-tbody');

  const idInput = byId('smb-server-id');
  const nameInput = byId('smb-name');
  const hostInput = byId('smb-host');
  const portInput = byId('smb-port');
  const userInput = byId('smb-username');
  const passInput = byId('smb-password');
  const shareInput = byId('smb-share-path');
  const modalTitle = byId('modal-smb-title');
  const testMessage = byId('smb-test-message');

  function resetForm() {
    if (idInput) idInput.value = '';
    if (nameInput) nameInput.value = '';
    if (hostInput) hostInput.value = '';
    if (portInput) portInput.value = '445';
    if (userInput) userInput.value = '';
    if (passInput) passInput.value = '';
    if (shareInput) shareInput.value = '';
    if (testMessage) {
      testMessage.style.display = 'none';
      testMessage.textContent = '';
      testMessage.className = 'section-message';
    }
    app.ui.clearFieldError(nameInput);
    app.ui.clearFieldError(hostInput);
    app.ui.clearFormAlert('smb-form-alert');
  }

  function openCreateModal(preset = null) {
    resetForm();
    if (modalTitle) modalTitle.textContent = '添加 SMB 服务器';
    if (preset) {
      if (nameInput) nameInput.value = preset.name || '';
      if (hostInput) hostInput.value = preset.host || '';
      if (portInput) portInput.value = String(preset.port || 445);
    }
    app.ui.openModal('modal-smb', addBtn);
  }

  function openEditModal(server) {
    if (!server) return;
    resetForm();
    if (modalTitle) modalTitle.textContent = '编辑 SMB 服务器';
    if (idInput) idInput.value = server.id || '';
    if (nameInput) nameInput.value = server.name || '';
    if (hostInput) hostInput.value = server.host || '';
    if (portInput) portInput.value = String(server.port || 445);
    if (userInput) userInput.value = server.username || '';
    if (shareInput) shareInput.value = server.share_path || '';
    app.ui.openModal('modal-smb', addBtn);
  }

  async function loadSmb(options = {}) {
    if (!tbody) return [];
    const silent = Boolean(options.silent);
    const requestKey = options.requestKey || 'smb:list';

    renderSkeletonRows(tbody, 5, 3);

    try {
      const list = await app.api.get('/smb/servers', { requestKey });
      const servers = Array.isArray(list) ? list : [];
      app.store.patch({ entities: { smbServers: servers } });

      if (servers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5"><div class="tp-empty-state"><div class="tp-empty-icon">💾</div><h4>暂无 SMB 服务器</h4><p>添加 NAS 或网络共享来管理媒体文件。</p></div></td></tr>';
        return servers;
      }

      tbody.innerHTML = servers
        .map((server) => {
          const connected = Boolean(server.is_connected);
          return `
            <tr>
              <td>${escapeHtml(server.name || '-')}</td>
              <td>${escapeHtml(server.host || '-')}</td>
              <td>${escapeHtml(server.username || '-')}</td>
              <td><span class="status-badge ${connected ? 'online' : 'offline'}">${connected ? '已连接' : '未连接'}</span></td>
              <td>
                <button type="button" class="cbi-button smb-edit" data-id="${escapeHtml(server.id)}">编辑</button>
                <button type="button" class="cbi-button cbi-button-remove smb-delete" data-id="${escapeHtml(server.id)}">删除</button>
              </td>
            </tr>
          `;
        })
        .join('');

      tbody.querySelectorAll('.smb-edit').forEach((btn) => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-id');
          const target = servers.find((item) => item.id === id);
          openEditModal(target);
        });
      });

      tbody.querySelectorAll('.smb-delete').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const ok = await app.ui.confirm('确定要删除该 SMB 服务器吗？', {
            title: '删除服务器',
            type: 'danger',
            okText: '删除',
          });
          if (!ok) return;

          app.ui.setButtonBusy(btn);
          try {
            await app.api.del(`/smb/servers/${btn.getAttribute('data-id')}`);
            app.ui.toast('success', 'SMB 服务器已删除');
            await loadSmb({ silent: true });
            app.bus.emit('smb:updated');
          } catch (err) {
            app.ui.toast('error', err.message || '删除失败');
          } finally {
            app.ui.clearButtonBusy(btn, '删除');
          }
        });
      });

      return servers;
    } catch (err) {
      if (err?.code === 'ABORTED') return [];
      if (!silent) app.ui.toast('error', err.message || 'SMB 列表加载失败');
      tbody.innerHTML = `<tr><td colspan="5"><div class="tp-empty-state"><div class="tp-empty-icon">⚠</div><h4>加载失败</h4><p>${escapeHtml(err.message || '请检查网络')}</p></div></td></tr>`;
      return [];
    }
  }

  async function scanSmb() {
    app.ui.setButtonBusy(scanBtn, '扫描中...');
    if (scanResult) scanResult.style.display = 'block';
    if (scanMessage) {
      scanMessage.textContent = '正在扫描局域网...';
      scanMessage.className = 'section-message';
    }
    renderSkeletonRows(scanTbody, 4, 2);

    try {
      const data = await app.api.post('/smb/discover', { timeout_seconds: 8 }, { requestKey: 'smb:discover', timeoutMs: 30000, logError: false });
      const list = data?.servers || [];
      if (scanMessage) {
        scanMessage.textContent = list.length ? `扫描成功，发现 ${list.length} 台 SMB 服务` : '未发现 SMB 服务';
        scanMessage.className = `section-message ${list.length ? 'success' : ''}`;
      }

      if (!list.length) {
        scanTbody.innerHTML = '<tr><td colspan="4">暂无</td></tr>';
        return;
      }

      scanTbody.innerHTML = list
        .map((item) => {
          const name = item.instance_name || item.host || '-';
          const host = item.host || '-';
          const port = item.port || 445;
          return `
            <tr>
              <td>${escapeHtml(name)}</td>
              <td>${escapeHtml(host)}</td>
              <td>${port}</td>
              <td><button type="button" class="cbi-button cbi-button-add smb-add-discovered" data-name="${escapeHtml(name)}" data-host="${escapeHtml(host)}" data-port="${port}">添加</button></td>
            </tr>
          `;
        })
        .join('');

      scanTbody.querySelectorAll('.smb-add-discovered').forEach((btn) => {
        btn.addEventListener('click', () => {
          openCreateModal({
            name: btn.getAttribute('data-name') || '',
            host: btn.getAttribute('data-host') || '',
            port: Number(btn.getAttribute('data-port') || 445),
          });
        });
      });
    } catch (err) {
      if (err?.code === 'ABORTED') return;
      if (scanMessage) {
        scanMessage.textContent = err.message || '扫描失败';
        scanMessage.className = 'section-message error';
      }
      if (scanTbody) scanTbody.innerHTML = '<tr><td colspan="4">-</td></tr>';
    } finally {
      app.ui.clearButtonBusy(scanBtn, '扫描 SMB');
    }
  }

  function showTestMessage(text, isError = false) {
    if (!testMessage) return;
    testMessage.style.display = 'block';
    testMessage.textContent = text;
    testMessage.className = `section-message ${isError ? 'error' : 'success'}`;
  }

  async function testConnection() {
    const host = (hostInput?.value || '').trim();
    const port = Number(portInput?.value || 445) || 445;
    const username = (userInput?.value || '').trim();
    const password = passInput?.value || '';

    if (!host) {
      app.ui.setFieldError(hostInput, '请输入主机地址');
      app.ui.showFormAlert('smb-form-alert', 'warning', '请输入主机地址。');
      return;
    }

    app.ui.setButtonBusy(testBtn, '测试中...');
    showTestMessage('正在测试连接...', false);

    try {
      const result = await app.api.post('/smb/servers/test', {
        host,
        port,
        username,
        password,
      });

      if (result?.success) {
        showTestMessage(`连接成功: ${result.message || 'OK'}`);
        app.ui.toast('success', 'SMB 连接测试成功');
      } else {
        showTestMessage(`连接失败: ${result?.message || '未知错误'}`, true);
        app.ui.toast('error', 'SMB 连接失败');
      }
    } catch (err) {
      showTestMessage(`连接失败: ${err.message || '请求失败'}`, true);
      app.ui.toast('error', err.message || '连接测试失败');
    } finally {
      app.ui.clearButtonBusy(testBtn, '测试连接');
    }
  }

  async function saveServer() {
    const id = idInput?.value || '';
    const payload = {
      name: (nameInput?.value || '').trim(),
      host: (hostInput?.value || '').trim(),
      port: Number(portInput?.value || 445) || 445,
      username: (userInput?.value || '').trim(),
      share_path: (shareInput?.value || '').trim(),
    };
    const password = passInput?.value || '';

    app.ui.clearFieldError(nameInput);
    app.ui.clearFieldError(hostInput);
    app.ui.clearFormAlert('smb-form-alert');

    if (!payload.name) {
      app.ui.setFieldError(nameInput, '请输入名称');
      app.ui.showFormAlert('smb-form-alert', 'warning', '请填写 SMB 名称。');
      return;
    }

    if (!payload.host) {
      app.ui.setFieldError(hostInput, '请输入主机地址');
      app.ui.showFormAlert('smb-form-alert', 'warning', '请填写主机地址。');
      return;
    }

    if (password) payload.password = password;

    const method = id ? 'put' : 'post';
    const path = id ? `/smb/servers/${id}` : '/smb/servers';
    const body = id ? payload : { ...payload, protocol: 'SMB', password: payload.password || '' };

    app.ui.setButtonBusy(saveBtn, '保存中...');

    try {
      await app.api[method](path, body);
      app.ui.toast('success', id ? 'SMB 服务器已更新' : 'SMB 服务器已添加');
      app.ui.closeModal('modal-smb');
      await loadSmb({ silent: true });
      app.bus.emit('smb:updated');
    } catch (err) {
      app.ui.showFormAlert('smb-form-alert', 'error', err.message || '保存失败');
    } finally {
      app.ui.clearButtonBusy(saveBtn, '保存');
    }
  }

  scanBtn?.addEventListener('click', scanSmb);
  addBtn?.addEventListener('click', () => openCreateModal());
  refreshBtn?.addEventListener('click', () => loadSmb());
  testBtn?.addEventListener('click', testConnection);
  saveBtn?.addEventListener('click', saveServer);

  return {
    onEnter(tab) {
      if (tab === 'smb') loadSmb({ silent: true });
    },
    loadSmb,
    openCreateModal,
  };
}
