import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type StrategyDetail } from '../../lib/api'
import { useStrategy } from '../../contexts/StrategyContext'

const MARKETS = ['A-Share', 'US Equity', 'Crypto', 'Futures', 'FX']

const STRATEGY_STYLES = [
  'Value',
  'Momentum',
  'Mean Reversion',
  'Trend Following',
  'Statistical Arbitrage',
  'Multi-factor',
  'Market Neutral',
  'Grid / Volatility',
]

const RISK_PROFILES: {
  id: string
  label: string
  labelZh: string
  constraints: { label: string; value: string }[]
}[] = [
  {
    id: 'conservative',
    label: 'Conservative',
    labelZh: '保守',
    constraints: [
      { label: '最大回撤', value: '≤ 8%' },
      { label: '单笔损失', value: '≤ 1%' },
      { label: '总暴露', value: '≤ 30%' },
    ],
  },
  {
    id: 'balanced',
    label: 'Balanced',
    labelZh: '均衡',
    constraints: [
      { label: '最大回撤', value: '≤ 15%' },
      { label: '单笔损失', value: '≤ 3%' },
      { label: '总暴露', value: '≤ 60%' },
    ],
  },
  {
    id: 'aggressive',
    label: 'Aggressive',
    labelZh: '激进',
    constraints: [
      { label: '最大回撤', value: '≤ 25%' },
      { label: '单笔损失', value: '≤ 5%' },
      { label: '总暴露', value: '≤ 90%' },
    ],
  },
  {
    id: 'custom',
    label: 'Custom',
    labelZh: '自定义',
    constraints: [{ label: '风控约束', value: '用户定义' }],
  },
]

interface StrategyDraft {
  id: string
  name: string
  status: string
  signalDefinition: string
  entryRules: string
  exitRules: string
  rebalanceFrequency: string
  positionSizing: string
  riskConstraints: string
  benchmark: string
}

interface TraceItem {
  agent: string
  message: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  time?: string
}

interface StrategyBuilderProps {
  onRefresh?: () => void
  onOpenStrategy?: (id: string) => void
  onNavigate?: (target: string) => void
}

function clipText(text: string, maxChars: number): string {
  const t = text.trim()
  if (!t) return ''
  if (t.length <= maxChars) return t
  return `${t.slice(0, maxChars)}…`
}

function frequencyLabel(freq: string): string {
  const map: Record<string, string> = {
    '1m': '1 分钟',
    '5m': '5 分钟',
    '15m': '15 分钟',
    '1h': '1 小时',
    '1d': '日频',
    '1w': '周频',
  }
  return map[freq] || freq || '未指定'
}

export default function StrategyBuilder({ onRefresh, onOpenStrategy, onNavigate }: StrategyBuilderProps) {
  const data = useStrategy()

  const [market, setMarket] = useState('A-Share')
  const [universe, setUniverse] = useState('')
  const [strategyStyle, setStrategyStyle] = useState('Value')
  const [riskProfile, setRiskProfile] = useState('balanced')
  const [nlBrief, setNlBrief] = useState(data.nlPrompt)

  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [actionNotice, setActionNotice] = useState<string | null>(null)

  const [draftResult, setDraftResult] = useState<StrategyDraft | null>(null)
  const [activeTab, setActiveTab] = useState<'trace' | 'draft'>('trace')

  const [traceItems, setTraceItems] = useState<TraceItem[]>([
    { agent: 'Research Agent', message: '等待策略概要...', status: 'pending' },
    { agent: 'Strategy Agent', message: '等待研究输出...', status: 'pending' },
    { agent: 'Risk Agent', message: '等待信号规则...', status: 'pending' },
    { agent: 'Backtest Agent', message: '等待风险验证...', status: 'pending' },
  ])
  const [showRawLogs, setShowRawLogs] = useState(false)
  const [rawFeed, setRawFeed] = useState(data.feed)

  const wsRef = useRef<WebSocket | null>(null)
  const generationDoneRef = useRef(false)
  const nlBriefRef = useRef(nlBrief)
  // eslint-disable-next-line react-hooks/refs
  nlBriefRef.current = nlBrief

  const riskProfileMeta = RISK_PROFILES.find((r) => r.id === riskProfile)
  const riskConstraintText = riskProfileMeta
    ? riskProfileMeta.constraints.map((c) => `${c.label} ${c.value}`).join(', ')
    : ''

  const buildDraftFromStrategyDetail = useCallback(
    (d: StrategyDetail, nlHint: string | null): StrategyDraft => {
      const metricParts: string[] = []
      if (d.sharpe != null) metricParts.push(`夏普 ${d.sharpe.toFixed(2)}`)
      if (d.maxDd != null) metricParts.push(`最大回撤 ${(d.maxDd * 100).toFixed(1)}%`)
      if (d.annualReturn != null) metricParts.push(`年化收益 ${(d.annualReturn * 100).toFixed(1)}%`)
      if (d.oosScore != null) metricParts.push(`样本外得分 ${d.oosScore.toFixed(2)}`)
      const metricsLine =
        metricParts.length > 0
          ? `流水线内模拟回测快照：${metricParts.join('；')}。`
          : '具体绩效以策略详情与后续正式回测为准。'

      const pipelineLine =
        d.recentEvents?.length > 0
          ? `管线轨迹（最近几步）：${d.recentEvents
              .slice(0, 5)
              .map((e) => `${e.stage} / ${e.event}`)
              .join(' → ')}。`
          : ''

      const desc = d.description?.trim()
      const signalDefinition = [
        desc ? `核心信号：${desc}` : `核心信号：基于 ${d.family} 风格生成候选标的与权重建议。`,
        d.universe ? `标的范围：${d.universe}` : null,
        `交易周期：${frequencyLabel(d.frequency)}`,
        `风险偏好：${RISK_PROFILES.find((r) => r.id === d.riskProfile)?.label ?? d.riskProfile}`,
        metricParts.length ? `验证快照：${metricParts.join('；')}` : null,
        '源码已归档在策略详情的「代码」页签，此处仅展示可审查的信号逻辑摘要。',
      ]
        .filter(Boolean)
        .join('\n')

      const briefLine = nlHint?.trim()
        ? `您在概要中的表述（节选）：${clipText(nlHint, 260)}`
        : '当前为按「最近更新时间」自动载入的策略；左侧概要可与本条独立，填写后点击生成将基于概要产生新版本。'

      const entryRules = [
        `因子族 / 风格：${d.family}`,
        `交易市场：${d.market}`,
        d.universe ? `股票池或标的范围：${d.universe}` : null,
        `生成时选择的策略类型（概要）：${strategyStyle}`,
        briefLine,
      ]
        .filter(Boolean)
        .join('\n')

      const exitRules = [
        '出场、止损与持仓长度等以生成代码中的逻辑为准（信号反转、阈值、时间止损等均在代码中实现）。',
        metricsLine,
        pipelineLine,
      ]
        .filter(Boolean)
        .join('\n')

      const bench =
        (d.universe ?? '').trim() || universe.trim() || '概要未填股票池时，可与详情中的 universe 字段或默认基准对照。'

      return {
        id: d.id,
        name: d.name,
        status: '草稿',
        signalDefinition,
        entryRules,
        exitRules,
        rebalanceFrequency: `元数据中的调仓周期字段：${frequencyLabel(d.frequency)}（请与代码内的再平衡/调仓实现对照）。`,
        positionSizing: `风险偏好（策略记录）：${d.riskProfile}。概要侧约束：${riskConstraintText || '未额外填写'}`,
        riskConstraints: riskConstraintText,
        benchmark: bench,
      }
    },
    [riskConstraintText, universe, strategyStyle]
  )

  useEffect(() => {
    if (generating) return
    if (!data.matrix?.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDraftResult(null)
      return
    }
    const latestId = data.matrix[0].id
    let canceled = false
    ;(async () => {
      try {
        const d = await api.strategy.detail(latestId)
        if (canceled) return
        setDraftResult(buildDraftFromStrategyDetail(d, null))
        setActiveTab('draft')
      } catch {
        if (!canceled) setDraftResult(null)
      }
    })()
    return () => {
      canceled = true
    }
  }, [data.matrix, generating, buildDraftFromStrategyDetail])

  useEffect(() => {
    if (!generating || !taskId) return

    let pollInterval: ReturnType<typeof setInterval> | null = null
    let closed = false
    generationDoneRef.current = false

    const updateTrace = (stage: string, status: TraceItem['status'], message: string) => {
      const agentMap: Record<string, string> = {
        queued: 'Research Agent',
        running: 'Strategy Agent',
        risk: 'Risk Agent',
        backtest: 'Backtest Agent',
        done: 'Backtest Agent',
        failed: 'Risk Agent',
      }
      const agent = agentMap[stage] || 'System'
      setTraceItems((prev) =>
        prev.map((item) =>
          item.agent === agent ? { ...item, status, message } : item
        )
      )
    }

    const clearPoll = () => {
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
    }

    const finishFailure = (errMsg: string) => {
      if (generationDoneRef.current || closed) return
      generationDoneRef.current = true
      clearPoll()
      updateTrace('backtest', 'failed', errMsg)
      setGenerating(false)
      onRefresh?.()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }

    const applyDraftFromWsDetail = (detail: Record<string, string | undefined>) => {
      setDraftResult({
        id: (detail.strategyId as string) || taskId,
        name: (detail.strategyName as string) || 'AI 生成策略',
        status: '草稿',
        signalDefinition:
          (detail.signalDefinition as string) ||
          '未能从服务端拉取完整策略说明；请刷新后打开「策略详情」查看代码与描述。',
        entryRules: (detail.entryRules as string) || '请从策略详情或重新生成获取入场逻辑说明。',
        exitRules: (detail.exitRules as string) || '请从策略详情或重新生成获取出场逻辑说明。',
        rebalanceFrequency: (detail.rebalanceFrequency as string) || '见策略元数据或代码中的调仓逻辑。',
        positionSizing: (detail.positionSizing as string) || '见概要中的风险偏好与详情中的风险字段。',
        riskConstraints: riskConstraintText,
        benchmark: (detail.benchmark as string) || universe || '见概要或详情中的基准设置。',
      })
      setActiveTab('draft')
    }

    const finishSuccess = async (opts: { strategyId: string | null; wsDetail?: Record<string, unknown> }) => {
      if (generationDoneRef.current || closed) return
      generationDoneRef.current = true
      clearPoll()

      updateTrace('backtest', 'completed', '回测完成')
      updateTrace('risk', 'completed', '约束验证通过')
      updateTrace('running', 'completed', '信号规则已生成')
      updateTrace('queued', 'completed', '市场标的已扫描')

      const sid = opts.strategyId
      let draftLoaded = false
      if (sid) {
        try {
          const d = await api.strategy.detail(sid)
          setDraftResult(
            buildDraftFromStrategyDetail(d, nlBriefRef.current.trim() || null)
          )
          setActiveTab('draft')
          draftLoaded = true
        } catch {
          draftLoaded = false
        }
      }
      if (!draftLoaded && opts.wsDetail && typeof opts.wsDetail === 'object') {
        applyDraftFromWsDetail(opts.wsDetail as Record<string, string | undefined>)
        draftLoaded = true
      }
      if (!draftLoaded) {
        setDraftResult({
          id: sid || taskId,
          name: sid ? `策略（${sid.slice(0, 8)}）` : 'AI 生成策略',
          status: '草稿',
          signalDefinition:
            '未能加载策略详情（可能网络或服务异常）。请稍后点击矩阵中的策略名称，或刷新页面再试。',
          entryRules: `任务 ID 片段：${taskId?.slice(0, 8) ?? '—'}；策略 ID：${sid?.slice(0, 8) ?? '—'}`,
          exitRules: '打开弹窗中的「策略详情」可查看完整版本与代码。',
          rebalanceFrequency: '—',
          positionSizing: riskConstraintText || '—',
          riskConstraints: riskConstraintText,
          benchmark: universe || '—',
        })
        setActiveTab('draft')
      }

      if (sid) onOpenStrategy?.(sid)
      setGenerating(false)
      onRefresh?.()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }

    const pollTaskOnce = async () => {
      if (closed || generationDoneRef.current) return
      try {
        const task = await api.strategy.getTask(taskId)
        setTaskStatus(task.status)
        setTaskProgress(task.progress)

        const feed = await api.strategy.getFeed()
        setRawFeed(feed)

        const done =
          task.status === 'succeeded' || task.status === 'done' || task.status === 'completed'
        if (done) {
          await finishSuccess({ strategyId: task.strategyId })
        } else if (task.status === 'failed') {
          finishFailure(task.error || 'Generation failed')
        }
      } catch (e) {
        console.error('Task poll error:', e)
      }
    }

    pollInterval = setInterval(() => void pollTaskOnce(), 1200)
    void pollTaskOnce()

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws/strategy-events`)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            type?: string
            taskId?: string
            stage?: string
            progress?: number
            agent?: string
            event?: string
            timestamp?: string
            detail?: Record<string, unknown> | string
          }
          if (msg.type !== 'strategy.event') return
          if (msg.taskId !== taskId) return

          setTaskStatus(msg.stage ?? '')
          setTaskProgress(typeof msg.progress === 'number' ? msg.progress : 0)

          const time = msg.timestamp
            ? new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })
            : '--:--:--'

          setRawFeed((prev) => {
            const agent = (msg.agent || 'system').replace(/^agent-/, '')
            const tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red' =
              msg.stage === 'failed' ? 'red' : msg.stage === 'done' ? 'green' : 'blue'
            return [{ time, agent, event: `[${msg.stage}] ${msg.event}`, tone }, ...prev]
          })

          if (msg.stage === 'running') updateTrace('running', 'running', '生成信号与再平衡规则...')
          if (msg.stage === 'risk') updateTrace('risk', 'running', '验证风控约束...')
          if (msg.stage === 'backtest') updateTrace('backtest', 'running', '运行回测模拟...')

          const isDone =
            msg.stage === 'done' || msg.stage === 'succeeded' || msg.stage === 'completed'
          if (isDone) {
            let detail: Record<string, unknown> = {}
            if (msg.detail != null) {
              if (typeof msg.detail === 'string') {
                try {
                  detail = JSON.parse(msg.detail) as Record<string, unknown>
                } catch {
                  detail = {}
                }
              } else {
                detail = msg.detail
              }
            }
            const strategyId =
              (detail.strategyId as string | undefined) ||
              (detail.strategy_id as string | undefined) ||
              null
            void finishSuccess({ strategyId, wsDetail: Object.keys(detail).length ? detail : undefined })
          } else if (msg.stage === 'failed' || msg.stage === 'error') {
            const d = msg.detail
            let err = 'Generation failed'
            if (d && typeof d === 'object' && 'error' in d) err = String((d as { error?: string }).error || err)
            finishFailure(err)
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => {
        /* HTTP poll still drives completion */
      }

      ws.onclose = () => {
        wsRef.current = null
      }
    }

    connectWs()

    return () => {
      closed = true
      clearPoll()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [
    generating,
    taskId,
    onRefresh,
    onOpenStrategy,
    riskConstraintText,
    universe,
    buildDraftFromStrategyDetail,
  ])

  const handleGenerate = async () => {
    if (!nlBrief.trim()) return

    setTraceItems([
      { agent: 'Research Agent', message: '扫描市场标的...', status: 'running' },
      { agent: 'Strategy Agent', message: '等待研究输出...', status: 'pending' },
      { agent: 'Risk Agent', message: '等待信号规则...', status: 'pending' },
      { agent: 'Backtest Agent', message: '等待风险验证...', status: 'pending' },
    ])
    setDraftResult(null)
    setRawFeed(data.feed)
    setGenerating(true)
    setTaskProgress(0)
    setTaskStatus('queued')
    setActiveTab('trace')

    try {
      const task = await api.strategy.createTask({
        prompt: nlBrief,
        market: market === 'A-Share' ? 'A' : market === 'US Equity' ? 'US' : market === 'Crypto' ? 'crypto' : 'A',
        riskProfile: riskProfile === 'custom' ? 'balanced' : riskProfile,
      })
      setTaskId(task.id)
      setTaskStatus(task.status)
    } catch (e) {
      console.error('Create task error:', e)
      setGenerating(false)
    }
  }

  const handleDraftAction = async (action: 'backtest' | 'review' | 'risk' | 'save') => {
    if (!draftResult) return
    setActionNotice(null)

    if (action === 'backtest') {
      setActionNotice('已进入回测实验室，可继续查看参数搜索与样本外验证。')
      onNavigate?.('backtest')
      return
    }

    if (action === 'review') {
      setActionNotice('已打开策略详情，请在概览、代码与流水线页签中审查信号逻辑。')
      onOpenStrategy?.(draftResult.id)
      return
    }

    if (action === 'risk') {
      setActionNotice('已进入风控与熔断页，可审查该草案的风险预算与约束。')
      onNavigate?.('risk')
      return
    }

    try {
      await api.strategy.update(draftResult.id, { status: 'draft' })
      setDraftResult((prev) => (prev ? { ...prev, status: '草稿' } : prev))
      setActionNotice('草稿已保存，策略状态已保持为草稿。')
      onRefresh?.()
    } catch (e) {
      setActionNotice(`保存失败：${String(e)}`)
    }
  }

  const riskMeta = RISK_PROFILES.find((r) => r.id === riskProfile)
  const hasOutput = generating || draftResult

  return (
    <div className="sb-shell">
      {/* ── body: left form + right output ── */}
      <div className="sb-body">

        {/* Left: 配置表单 */}
        <div className="sb-left">
          <div className="sb-section-label">市场</div>
          <div className="sb-chips">
            {MARKETS.map((m) => (
              <button
                key={m}
                className={`sb-chip ${market === m ? 'active' : ''}`}
                onClick={() => setMarket(m)}
                disabled={generating}
              >
                {m}
              </button>
            ))}
          </div>

          <div className="sb-section-label">股票池</div>
          <input
            className="sb-input"
            value={universe}
            onChange={(e) => setUniverse(e.target.value)}
            placeholder="沪深 300 / S&P 500 / BTC 永续"
            disabled={generating}
          />

          <div className="sb-section-label">策略类型</div>
          <select
            className="sb-select"
            value={strategyStyle}
            onChange={(e) => setStrategyStyle(e.target.value)}
            disabled={generating}
          >
            {STRATEGY_STYLES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <div className="sb-section-label">风险偏好</div>
          <div className="sb-risk-row">
            {RISK_PROFILES.map((r) => (
              <button
                key={r.id}
                className={`sb-risk-btn ${riskProfile === r.id ? 'active' : ''}`}
                onClick={() => setRiskProfile(r.id)}
                disabled={generating}
              >
                <span className="sb-risk-en">{r.label}</span>
                <span className="sb-risk-zh">{r.labelZh}</span>
              </button>
            ))}
          </div>
          {riskMeta && (
            <div className="sb-constraints">
              {riskMeta.constraints.map((c, i) => (
                <div className="sb-constraint-row" key={i}>
                  <span>{c.label}</span>
                  <strong>{c.value}</strong>
                </div>
              ))}
            </div>
          )}

          <div className="sb-section-label">AI 自然语言描述</div>
          <textarea
            className="sb-textarea"
            value={nlBrief}
            onChange={(e) => setNlBrief(e.target.value)}
            rows={6}
            placeholder="例如：创建一个周频调仓的A股多因子价值策略，要求 ROE > 15%、PE 分位数 < 30%、流动性过滤、最大回撤不超过 15%、基准为沪深 300。"
            disabled={generating}
          />
        </div>

        {/* Right: 生成追踪 / 策略草案 */}
        <div className="sb-right">
          {/* Tab bar — shown only when there's output */}
          {hasOutput && (
            <div className="sb-tab-bar">
              <button
                className={`sb-tab ${activeTab === 'trace' ? 'active' : ''}`}
                onClick={() => setActiveTab('trace')}
              >
                <span className="sb-tab-dot" style={{ background: generating ? 'var(--blue)' : draftResult ? 'var(--green)' : 'var(--subtle)' }} />
                生成追踪
              </button>
              <button
                className={`sb-tab ${activeTab === 'draft' ? 'active' : ''} ${!draftResult ? 'disabled' : ''}`}
                onClick={() => { if (draftResult) setActiveTab('draft') }}
                disabled={!draftResult}
              >
                策略草案
                {draftResult && <span className="sb-tab-badge">就绪</span>}
              </button>
            </div>
          )}

          {/* Empty state */}
          {!hasOutput && (
            <div className="sb-empty">
              <div className="sb-empty-glyph">◈</div>
              <p className="sb-empty-title">填写左侧配置，点击「生成策略草案」</p>
              <p className="sb-empty-sub">AI Agent 将扫描市场、生成信号规则并完成初步回测验证</p>
              <div className="sb-empty-steps">
                <div className="sb-empty-step"><span>01</span>Research Agent 扫描标的池</div>
                <div className="sb-empty-step"><span>02</span>Strategy Agent 生成信号逻辑</div>
                <div className="sb-empty-step"><span>03</span>Risk Agent 验证约束</div>
                <div className="sb-empty-step"><span>04</span>Backtest Agent 回测模拟</div>
              </div>
            </div>
          )}

          {/* Trace tab */}
          {hasOutput && activeTab === 'trace' && (
            <div className="sb-trace-panel">
              {/* Progress bar */}
              {generating && (
                <div className="sb-progress-wrap">
                  <div className="sb-progress-bar">
                    <div className="sb-progress-fill" style={{ width: `${taskProgress}%` }} />
                  </div>
                  <span className="sb-progress-label">{taskStatus || 'queued'} · {taskProgress}%</span>
                </div>
              )}

              {/* Trace items */}
              <div className="sb-trace-list">
                {traceItems.map((item, i) => (
                  <div className={`sb-trace-item sb-trace-${item.status}`} key={i}>
                    <div className="sb-trace-icon">
                      {item.status === 'completed' && <span className="sb-ti-check">✓</span>}
                      {item.status === 'running' && <span className="sb-ti-spin" />}
                      {item.status === 'failed' && <span className="sb-ti-fail">✗</span>}
                      {item.status === 'pending' && <span className="sb-ti-pending" />}
                    </div>
                    <div className="sb-trace-body">
                      <strong>{item.agent}</strong>
                      <span>{item.message}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Raw logs toggle */}
              <button className="sb-log-toggle" onClick={() => setShowRawLogs((v) => !v)}>
                {showRawLogs ? '▲ 收起原始日志' : '▼ 展开原始 Agent 日志'}
              </button>
              {showRawLogs && (
                <div className="sb-raw-logs">
                  {rawFeed.slice(0, 30).map((f, i) => (
                    <div className={`sb-raw-row raw-${f.tone}`} key={i}>
                      <span className="sb-raw-time">{f.time}</span>
                      <span className="sb-raw-agent">{f.agent}</span>
                      <span className="sb-raw-event">{f.event}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Draft tab */}
          {hasOutput && activeTab === 'draft' && draftResult && (
            <div className="sb-draft-panel">
              <div className="sb-draft-header">
                <span className="sb-draft-badge">草稿</span>
                <h3 className="sb-draft-name">{draftResult.name}</h3>
                <span className="sb-draft-id">#{draftResult.id.slice(0, 8)}</span>
              </div>

              <div className="sb-draft-body">
                {[
                  { label: '信号定义', value: draftResult.signalDefinition },
                  { label: '入场规则', value: draftResult.entryRules },
                  { label: '出场规则', value: draftResult.exitRules },
                  { label: '调仓频率', value: draftResult.rebalanceFrequency },
                  { label: '仓位管理', value: draftResult.positionSizing },
                  { label: '风控约束', value: draftResult.riskConstraints },
                  { label: '基准', value: draftResult.benchmark },
                ].map(({ label, value }) => (
                  <div className="sb-draft-section" key={label}>
                    <div className="sb-draft-section-label">{label}</div>
                    <p className="sb-draft-section-text">{value}</p>
                  </div>
                ))}
              </div>

              {/* Next actions */}
              <div className="sb-next-actions">
                <div className="sb-next-label">下一步操作</div>
                <div className="sb-next-grid">
                  <button className="sb-next-btn primary" onClick={() => void handleDraftAction('backtest')}>
                    <span className="sb-next-icon">⚡</span>
                    <span className="sb-next-text">
                      <strong>运行回测</strong>
                      <em>历史数据验证</em>
                    </span>
                  </button>
                  <button className="sb-next-btn" onClick={() => void handleDraftAction('review')}>
                    <span className="sb-next-icon">🔍</span>
                    <span className="sb-next-text">
                      <strong>审查信号逻辑</strong>
                      <em>查看代码与详情</em>
                    </span>
                  </button>
                  <button className="sb-next-btn" onClick={() => void handleDraftAction('risk')}>
                    <span className="sb-next-icon">🛡</span>
                    <span className="sb-next-text">
                      <strong>风控检查</strong>
                      <em>验证风险约束</em>
                    </span>
                  </button>
                  <button className="sb-next-btn" onClick={() => void handleDraftAction('save')}>
                    <span className="sb-next-icon">💾</span>
                    <span className="sb-next-text">
                      <strong>保存草稿</strong>
                      <em>归档当前版本</em>
                    </span>
                  </button>
                </div>
                {actionNotice && (
                  <div className="sb-action-notice">{actionNotice}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Sticky footer ── */}
      <div className="sb-footer">
        <button className="sb-footer-secondary" disabled={generating}>
          保存为模板
        </button>
        <div className="sb-footer-right">
          {generating && (
            <div className="sb-footer-status">
              <span className="sb-footer-spinner" />
              <span>Strategy Agent 生成中 · {taskProgress}%</span>
            </div>
          )}
          <button
            className="sb-footer-cta"
            onClick={handleGenerate}
            disabled={generating || !nlBrief.trim()}
          >
            {generating ? `生成中 ${taskProgress}%` : '生成策略草案'}
            {!generating && <span className="sb-footer-arrow">→</span>}
          </button>
        </div>
      </div>
    </div>
  )
}
