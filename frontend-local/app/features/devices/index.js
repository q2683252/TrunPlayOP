import { byId, escapeHtml, renderSkeletonRows } from '../../core/helpers.js';

export function registerDevices(app) {
  const tbody = byId('devices-tbody');
  const discoverBtn = byId('btn-discover');
  const refreshBtn = byId('btn-refresh-devices');
  const addBtn = byId('btn-add-device');
  const saveBtn = byId('btn-save-device');

  const addressInput = byId('device-address');
  const portInput = byId('device-port');

  function isValidIpv4(value) {
    if (!value) return false;
    const parts = value.split('.');
    if (parts.length !== 4) return false;
    return parts.every((part) => {
      if (!/^\d+$/.test(part)) return false;
      if (part.length > 1 && part.startsWith('0')) return false;
      const num = Number(part);
      return num >= 0 && num <= 255;
    });
  }

  async function loadDevices(options = {}) {
    if (!tbody) return [];
    const silent = Boolean(options.silent);
    const requestKey = options.requestKey || 'devices:list';

    renderSkeletonRows(tbody, 5, 3);

    try {
      const list = await app.api.get('/devices', { requestKey });
      const devices = Array.isArray(list) ? list : [];
      app.store.patch({ entities: { devices } });

      if (devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5"><div class="tp-empty-state"><div class="tp-empty-icon">📺</div><h4>暂无设备</h4><p>点击「扫描设备」发现局域网内的投屏设备。</p></div></td></tr>';
        return devices;
      }

      tbody.innerHTML = devices
        .map((device) => {
          const online = Boolean(device.is_online);
          return `
            <tr>
              <td>${escapeHtml(device.name || '-')}</td>
              <td>${escapeHtml(device.address || '-')}</td>
              <td>${escapeHtml(device.type || '-')}</td>
              <td><span class="status-badge ${online ? 'online' : 'offline'}">${online ? '在线' : '离线'}</span></td>
              <td>
                <button type="button" class="cbi-button cbi-button-remove device-delete" data-id="${escapeHtml(device.id)}">删除</button>
              </td>
            </tr>
          `;
        })
        .join('');

      tbody.querySelectorAll('.device-delete').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const ok = await app.ui.confirm('确定要删除该设备吗？', {
            title: '删除设备',
            type: 'danger',
            okText: '删除',
          });
          if (!ok) return;

          app.ui.setButtonBusy(btn);
          try {
            await app.api.del(`/devices/${btn.getAttribute('data-id')}`);
            app.ui.toast('success', '设备已删除');
            await loadDevices({ silent: true });
          } catch (err) {
            app.ui.toast('error', err.message || '删除失败');
          } finally {
            app.ui.clearButtonBusy(btn, '删除');
          }
        });
      });

      return devices;
    } catch (err) {
      if (err?.code === 'ABORTED') return [];
      if (!silent) app.ui.toast('error', err.message || '设备加载失败');
      tbody.innerHTML = `<tr><td colspan="5"><div class="tp-empty-state"><div class="tp-empty-icon">⚠</div><h4>加载失败</h4><p>${escapeHtml(err.message || '请检查网络')}</p></div></td></tr>`;
      return [];
    }
  }

  async function discoverDevices() {
    app.ui.setButtonBusy(discoverBtn, '扫描中...');
    app.ui.toast('info', '正在扫描局域网设备...', 2600);
    try {
      const result = await app.api.post('/devices/discover', {}, { requestKey: 'devices:discover', timeoutMs: 30000, logError: false });
      const count = result?.devices?.length || 0;
      app.ui.toast('success', `扫描完成，发现 ${count} 台设备`);
      await loadDevices({ silent: true });
    } catch (err) {
      if (err?.code !== 'ABORTED') app.ui.toast('error', err.message || '扫描失败');
    } finally {
      app.ui.clearButtonBusy(discoverBtn, '扫描设备');
    }
  }

  function openCreateModal() {
    if (addressInput) addressInput.value = '';
    if (portInput) portInput.value = '8200';
    app.ui.clearFieldError(addressInput);
    app.ui.showFormAlert('device-form-alert', '', '');
    app.ui.openModal('modal-device', addBtn);
  }

  async function saveDevice() {
    const address = (addressInput?.value || '').trim();
    const port = Number(portInput?.value || 8200) || 8200;

    app.ui.clearFieldError(addressInput);
    app.ui.clearFormAlert('device-form-alert');

    if (!address) {
      app.ui.setFieldError(addressInput, '请输入设备 IP 地址');
      app.ui.showFormAlert('device-form-alert', 'warning', '请输入设备 IP 地址。');
      return;
    }

    if (!isValidIpv4(address)) {
      app.ui.setFieldError(addressInput, '请输入有效的 IPv4 地址（例如 192.168.1.100）');
      app.ui.showFormAlert('device-form-alert', 'warning', 'IP 地址格式不正确，请使用 IPv4 地址。');
      return;
    }

    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      app.ui.showFormAlert('device-form-alert', 'warning', '端口范围应在 1-65535。');
      return;
    }

    app.ui.setButtonBusy(saveBtn, '添加中...');
    try {
      await app.api.post('/devices/add', { address, port });
      app.ui.toast('success', '设备已添加');
      app.ui.closeModal('modal-device');
      await loadDevices({ silent: true });
    } catch (err) {
      app.ui.showFormAlert('device-form-alert', 'error', err.message || '添加失败');
    } finally {
      app.ui.clearButtonBusy(saveBtn, '添加');
    }
  }

  discoverBtn?.addEventListener('click', discoverDevices);
  refreshBtn?.addEventListener('click', () => loadDevices());
  addBtn?.addEventListener('click', openCreateModal);
  saveBtn?.addEventListener('click', saveDevice);

  return {
    onEnter(tab) {
      if (tab === 'devices') loadDevices({ silent: true });
    },
    loadDevices,
    openCreateModal,
  };
}
