// 科研进度面板插件 —— Client 半身（动态 Cordis 插件 code.client）
// 职责：在 shell.overlay 注册右下角浮动面板，每 4 秒轮询 host.call('research-progress:get') 渲染。
// 本文件内容即 cordis_define 的 code.client 字段（函数体，原样传入）。
return {
  inject: ['slots', 'timer'],
  apply(ctx) {
    styles.insert(`
      .ar-panel { position: fixed; right: 16px; bottom: 16px; width: 320px; max-width: calc(100vw - 32px);
        background: var(--dsw-alias-bg-overlay); border: 1px solid var(--dsw-alias-border-l2);
        border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.30); color: var(--dsw-alias-label-primary);
        font: 13px/1.5 -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; pointer-events: auto;
        z-index: 2147483000; overflow: hidden; }
      .ar-panel-head { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .ar-panel-title { font-weight: 600; font-size: 13px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ar-chip { font-size: 11px; padding: 1px 8px; border-radius: 99px; border: 1px solid var(--dsw-alias-border-l2); color: var(--dsw-alias-label-secondary); }
      .ar-chip.done { color: var(--dsw-alias-state-success-primary); border-color: var(--dsw-alias-state-success-primary); }
      .ar-chip.blocked { color: var(--dsw-alias-state-error-primary); border-color: var(--dsw-alias-state-error-primary); }
      .ar-chip.running, .ar-chip.planning { color: var(--dsw-alias-brand-primary); border-color: var(--dsw-alias-brand-primary); }
      .ar-toggle { background: none; border: none; color: var(--dsw-alias-label-secondary); cursor: pointer; font-size: 13px; padding: 0 2px; }
      .ar-body { padding: 10px 12px 12px; }
      .ar-task { font-weight: 600; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; word-break: break-all; }
      .ar-bar { height: 8px; border-radius: 99px; background: var(--dsw-alias-bg-layer-1); border: 1px solid var(--dsw-alias-border-l1); overflow: hidden; }
      .ar-bar > div { height: 100%; background: var(--dsw-alias-brand-primary); border-radius: 99px; transition: width .4s ease; }
      .ar-pct { font-size: 11px; color: var(--dsw-alias-label-secondary); margin: 4px 0 10px; text-align: right; }
      .ar-phase { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
      .ar-phase .st { width: 14px; text-align: center; flex: none; }
      .ar-phase .nm { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ar-minibar { width: 48px; height: 5px; border-radius: 99px; background: var(--dsw-alias-bg-layer-1); border: 1px solid var(--dsw-alias-border-l1); overflow: hidden; flex: none; }
      .ar-minibar > div { height: 100%; border-radius: 99px; transition: width .4s ease; }
      .ar-minibar.running > div { background: var(--dsw-alias-brand-primary); }
      .ar-minibar.done > div { background: var(--dsw-alias-state-success-primary); }
      .ar-minibar.blocked > div { background: var(--dsw-alias-state-error-primary); }
      .ar-note { margin-top: 8px; font-size: 12px; color: var(--dsw-alias-label-secondary); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
      .ar-meta { margin-top: 8px; font-size: 11px; color: var(--dsw-alias-label-secondary); display: flex; justify-content: space-between; gap: 8px; }
      .ar-idle { padding: 18px 12px; text-align: center; color: var(--dsw-alias-label-secondary); font-size: 12px; white-space: pre-line; }
    `)

    const STATUS_ICON = { done: '✓', running: '●', blocked: '✕', pending: '○' }
    const STATUS_LABEL = { idle: '空闲', queued: '排队', planning: '规划中', running: '执行中', blocked: '受阻', done: '已完成' }

    function fmtTime(iso) {
      if (!iso) return ''
      try {
        const d = new Date(iso)
        if (Number.isNaN(d.getTime())) return ''
        return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
      } catch (e) {
        return ''
      }
    }

    function ProgressPanel() {
      const [data, setData] = React.useState(null)
      const [collapsed, setCollapsed] = React.useState(false)

      React.useEffect(() => {
        let alive = true
        const tick = () => {
          host.call('research-progress:get', {}).then((res) => {
            if (alive && res && res.state) setData(res.state)
          }).catch(() => {})
        }
        tick()
        const disposer = ctx.interval(tick, 4000)
        return () => {
          alive = false
          if (disposer) disposer()
        }
      }, [])

      if (!data || data.status === 'idle' || data.status === 'queued') {
        return React.createElement('div', { className: 'ar-panel' },
          React.createElement('div', { className: 'ar-panel-head' },
            React.createElement('span', { className: 'ar-panel-title' }, '🧪 自动化科研'),
            React.createElement('span', { className: 'ar-chip' }, '空闲')),
          React.createElement('div', { className: 'ar-idle' }, '暂无进行中的科研任务\n睡前发布任务，早晨查看结果'))
      }

      const chipCls = 'ar-chip ' + (data.status === 'done' ? 'done' : data.status === 'blocked' ? 'blocked' : (data.status === 'running' || data.status === 'planning') ? 'running' : '')
      const modeText = data.mode && data.mode.name ? data.mode.name + (data.mode.customized ? '·已定制' : '') : ''
      const head = React.createElement('div', { className: 'ar-panel-head' },
        React.createElement('span', { className: 'ar-panel-title', title: data.title }, '🧪 自动化科研'),
        modeText ? React.createElement('span', { className: 'ar-chip running', title: data.mode && data.mode.axes ? '轴档位: L' + data.mode.axes.L + ' · A' + data.mode.axes.A + ' · ' + data.mode.axes.R + ' · T' + data.mode.axes.T + ' · ' + data.mode.axes.M : '' }, modeText) : null,
        React.createElement('span', { className: chipCls }, STATUS_LABEL[data.status] || data.status),
        React.createElement('button', { className: 'ar-toggle', onClick: () => setCollapsed(!collapsed), title: collapsed ? '展开' : '收起' }, collapsed ? '▲' : '▼'))

      if (collapsed) return React.createElement('div', { className: 'ar-panel' }, head)

      const phaseColor = (p) => p.status === 'done'
        ? 'var(--dsw-alias-state-success-primary)'
        : p.status === 'blocked' ? 'var(--dsw-alias-state-error-primary)'
        : p.status === 'running' ? 'var(--dsw-alias-brand-primary)' : undefined

      const phases = (data.phases || []).map((p) =>
        React.createElement('div', { className: 'ar-phase', key: p.id || p.name },
          React.createElement('span', { className: 'st', style: { color: phaseColor(p) } }, STATUS_ICON[p.status] || '○'),
          React.createElement('span', { className: 'nm', title: p.name + (p.note ? ' — ' + p.note : '') }, p.name),
          React.createElement('span', { className: 'ar-minibar ' + p.status },
            React.createElement('div', { style: { width: p.percent + '%' } })),
          React.createElement('span', { className: 'pp' }, p.percent + '%')))

      return React.createElement('div', { className: 'ar-panel' },
        head,
        React.createElement('div', { className: 'ar-body' },
          React.createElement('div', { className: 'ar-task', title: data.title }, data.title),
          React.createElement('div', { className: 'ar-bar' },
            React.createElement('div', { style: { width: data.overallPercent + '%' } })),
          React.createElement('div', { className: 'ar-pct' }, '总进度 ' + data.overallPercent + '%'),
          phases,
          data.note ? React.createElement('div', { className: 'ar-note' }, '▸ ' + data.note) : null,
          React.createElement('div', { className: 'ar-meta' },
            React.createElement('span', null, '更新 ' + fmtTime(data.lastUpdatedAt)),
            data.deadline ? React.createElement('span', null, '截止 ' + fmtTime(data.deadline)) : null)))
    }

    const slots = ctx.get('slots')
    if (slots === undefined) return
    slots.inject('shell.overlay', () => slots.register(
      { name: 'shell.overlay', id: 'research-progress-panel', order: 100 },
      () => React.createElement(ProgressPanel, null),
    ))
  },
}
