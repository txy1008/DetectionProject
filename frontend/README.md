# 智慧路口视频监控系统前端

基于 Vue3 + Vite + Element Plus + Tailwind CSS 构建。

## 路由

- `/` 首页
- `/services` 服务能力
- `/detection` 检测中心
- `/analysis` 数据分析
- `/about` 关于我们

## 启动

```bash
npm install
npm run dev
```

## 后端对接

Vite 已配置 `/api` 代理，默认转发到：

```text
http://127.0.0.1:8000
```

如果后端使用 Flask，可将 `vite.config.js` 中的 `target` 改为 `http://127.0.0.1:5000`。
