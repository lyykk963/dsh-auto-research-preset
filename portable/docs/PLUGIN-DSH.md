# （可选）DSH 进度面板

只有 DSH 宿主有右下角实时面板。它由两个文件组成，**不在本可移植包内**：

- `plugin-host.js`：读写 `progress.json`、注册 `update_research_progress` 工具
- `plugin-client.js`：右下角浮动面板，每 4 秒轮询

源码位置：`%APPDATA%\dsh-desktop\harness\.agent-presets\auto-research\skills\auto-research\`

在 DSH 里它由 `agent.cordis.yml` 的启动协议自动装配。
**搬去别的宿主时不需要它**——进度文件协议本身就是完整的，只是没有可视化。
