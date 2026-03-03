# TrunPlay 本地前端

与 TrunPlay 后端配合使用的静态前端，在浏览器中直接请求后端 API（无需 LuCI 代理）。

## 前提

1. **后端已运行**：在项目根目录或 `trunplay-backend` 下启动后端，API 默认在 `http://127.0.0.1:8088`。
2. **CORS**：后端默认已允许来源 `http://localhost:3000` 和 `http://127.0.0.1:3000`，前端在 3000 端口启动即可跨域请求。

## 启动前端

在 **本目录**（`frontend-local/`）下起一个静态 HTTP 服务，端口 **3000**。

### 方式一：Python 3

```bash
cd frontend-local
python3 -m http.server 3000
```

### 方式二：使用脚本

```bash
./serve.sh
```

（脚本内部也是执行 `python3 -m http.server 3000`，若 3000 被占用可改脚本中的端口。）

### 方式三：Node.js（若已安装 npx）

```bash
cd frontend-local
npx serve -l 3000
```

## 访问

浏览器打开：

- http://localhost:3000
- 或 http://127.0.0.1:3000

即可使用：状态总览、学习任务、设备管理、SMB 存储、播放历史。  
前端会请求 `http://127.0.0.1:8088/api/v1`，请确保后端已启动且端口一致。

## 新版前端结构（ES Modules）

- 入口：`app/boot.js`
- 核心模块：`app/core/{api-client,store,router,ui-feedback}.js`
- 功能模块：`app/features/{status,plans,study,devices,smb,history,onboarding}/index.js`
- 样式分层：`styles/tokens.css`、`styles/components.css`、`styles/pages/*.css`

### Hash 路由

支持直接访问或分享当前页：

- `#status`
- `#study`
- `#devices`
- `#smb`
- `#history`

## 修改 API 地址

如需连其他主机或端口，编辑 `app/core/constants.js`：

```javascript
export const API_BASE = `${apiProtocol}//${apiHost}:8088/api/v1`;
```

改为你的后端地址（例如 `http://192.168.1.1:8088/api/v1`）。

## 本地存储键

- `tp:last_tab`：记住上次停留页面。
- `tp:onboarding_dismissed`：首次引导卡片的隐藏状态。
