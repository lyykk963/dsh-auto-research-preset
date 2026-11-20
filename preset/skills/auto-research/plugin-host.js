// 科研进度面板插件 —— Host 半身（动态 Cordis 插件 code.host）
// 职责：读写 <工作区>/.dsh-research/progress.json；注册 update_research_progress 工具；
//       注册 research-progress:get / research-progress:set RPC 供 Client 半身调用。
// 本文件内容即 cordis_define 的 code.host 字段（函数体，原样传入）。
return {
  inject: ['fs'],
  apply(ctx) {
    let targetPath = null

    const STATUSES = ['idle', 'queued', 'planning', 'running', 'blocked', 'done']
    const PHASE_STATUSES = ['pending', 'running', 'blocked', 'done']

    function normalize(state) {
      const phases = Array.isArray(state.phases)
        ? state.phases.filter((p) => p && typeof p === 'object').map((p) => ({
            id: String(p.id || ''),
            name: String(p.name || p.id || '阶段'),
            status: PHASE_STATUSES.includes(p.status) ? p.status : 'pending',
            percent: Math.max(0, Math.min(100, Math.round(Number(p.percent) || 0))),
            startedAt: p.startedAt || null,
            finishedAt: p.finishedAt || null,
            note: String(p.note || ''),
          }))
        : []
      let overall = Math.max(0, Math.min(100, Math.round(Number(state.overallPercent) || 0)))
      if ((state.overallPercent === undefined || state.overallPercent === null) && phases.length > 0) {
        overall = Math.round(phases.reduce((s, p) => s + p.percent, 0) / phases.length)
      }
      return {
        version: 1,
        taskId: String(state.taskId || ''),
        title: String(state.title || '科研任务'),
        status: STATUSES.includes(state.status) ? state.status : 'running',
        mode: state.mode && typeof state.mode === 'object' ? {
          id: String(state.mode.id || ''),
          name: String(state.mode.name || ''),
          customized: state.mode.customized === true,
          axes: state.mode.axes && typeof state.mode.axes === 'object' ? state.mode.axes : null,
        } : null,
        deadline: state.deadline || null,
        publishedAt: state.publishedAt || null,
        currentPhaseId: state.currentPhaseId || null,
        overallPercent: overall,
        phases,
        reportPath: state.reportPath || null,
        note: String(state.note || ''),
        lastUpdatedAt: state.lastUpdatedAt || null,
      }
    }

    async function readState(path) {
      try {
        const target = await ctx.fs.resolve(path, {})
        const info = await ctx.fs.stat(target)
        if (!info) return null
        const text = await ctx.fs.readText(target)
        return JSON.parse(text)
      } catch (error) {
        return null
      }
    }

    // 按固定约定 <工作区>/.dsh-research/progress.json 从路径推导 workspace-write 策略根，
    // 插件无会话上下文，默认策略根是进程级目录，会拒绝工作区外的写入。
    // 注意：路径分隔符用 String.fromCharCode(92) 构造，避免源码反斜杠在 JSON 传输中被转义破坏。
    function policyFor(path) {
      const bs = String.fromCharCode(92)
      const s = String(path).split(bs).join('/')
      const tail = '/.dsh-research/progress.json'
      if (s.toLowerCase().endsWith(tail) === false) return null
      return { mode: 'workspace-write', workspaceRoot: s.slice(0, s.length - tail.length) }
    }

    async function writeState(path, state) {
      const target = await ctx.fs.resolve(path, {})
      const policy = policyFor(path)
      await ctx.fs.writeText(target, JSON.stringify(state, null, 2), undefined, undefined, policy)
    }

    harness.handle('research-progress:get', async (args) => {
      const path = (args && typeof args.path === 'string' && args.path) || targetPath
      if (!path) return { state: normalize({ status: 'idle' }), source: 'none' }
      const raw = await readState(path)
      return { state: normalize(raw || { status: 'idle' }), source: raw ? 'file' : 'missing' }
    })

    harness.handle('research-progress:set', async (args) => {
      const path = args && typeof args.path === 'string' && args.path
      if (!path) return { ok: false, error: 'path required' }
      if (!args.state || typeof args.state !== 'object') return { ok: false, error: 'state required' }
      const state = normalize(args.state)
      await writeState(path, state)
      targetPath = path
      return { ok: true, state }
    })

    harness.registerTool(ctx, harness.defineTool({
      name: 'update_research_progress',
      description: '更新科研任务进度（驱动网页右下角进度面板）。每个阶段/里程碑后调用。path 为进度文件绝对路径（固定 <工作区>/.dsh-research/progress.json），state 为进度对象（schema 见 auto-research skill 第 2 节：{status,title,taskId,deadline,publishedAt,currentPhaseId,overallPercent,phases[],reportPath,note}）。',
      parameters: {
        path: { type: 'string', required: true, description: '进度文件绝对路径，如 D:\\research\\.dsh-research\\progress.json' },
        state: { type: 'object', required: true, additionalProperties: true, description: '进度对象，schema 见 auto-research skill 第 2 节' },
      },
      output: { schema: { type: 'string' }, render(_a, v) { return [{ type: 'text', text: v }] } },
      async execute(args) {
        const path = typeof args.path === 'string' && args.path
        if (!path) return 'ERROR: path 必填（进度文件绝对路径）'
        if (!args.state || typeof args.state !== 'object') return 'ERROR: state 必填（进度对象）'
        const state = normalize(args.state)
        try {
          await writeState(path, state)
          targetPath = path
          const phases = state.phases.map((p) => p.name + ':' + p.status).join(', ')
          return '进度已更新 -> status=' + state.status + ' overall=' + state.overallPercent + '% currentPhase=' + (state.currentPhaseId || '-') + ' 阶段: ' + (phases || '无')
        } catch (error) {
          return 'ERROR: 写入失败 ' + String((error && error.message) || error) + '（path 必须符合约定 <工作区>/.dsh-research/progress.json）'
        }
      },
    }))
  },
}
