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
  constraints: { label: string; value: string }[]
}[] = [
  {
    id: 'conservative',
    label: 'Conservative',
    constraints: [
      { label: 'Max Drawdown', value: '≤ 8%' },
      { label: 'Single trade loss', value: '≤ 1%' },
      { label: 'Gross Exposure', value: '≤ 30%' },
    ],
  },
  {
    id: 'balanced',
    label: 'Balanced',
    constraints: [
      { label: 'Max Drawdown', value: '≤ 15%' },
      { label: 'Single trade loss', value: '≤ 3%' },
      { label: 'Gross Exposure', value: '≤ 60%' },
    ],
  },
  {
    id: 'aggressive',
    label: 'Aggressive',
    constraints: [
      { label: 'Max Drawdown', value: '≤ 25%' },
      { label: 'Single trade loss', value: '≤ 5%' },
      { label: 'Gross Exposure', value: '≤ 90%' },
    ],
  },
  {
    id: 'custom',
    label: 'Custom',
    constraints: [{ label: 'Risk constraints', value: 'User-defined' }],
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

  // Strategy Brief form state
  const [market, setMarket] = useState('A-Share')
  const [universe, setUniverse] = useState('')
  const [strategyStyle, setStrategyStyle] = useState('Value')
  const [riskProfile, setRiskProfile] = useState('balanced')
  const [nlBrief, setNlBrief] = useState(data.nlPrompt)

  // Generation state
  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [actionNotice, setActionNotice] = useState<string | null>(null)

  // Draft result
  const [draftResult, setDraftResult] = useState<StrategyDraft | null>(null)

  // Trace state
  const [traceItems, setTraceItems] = useState<TraceItem[]>([
    { agent: 'Research Agent', message: 'Waiting for strategy brief...', status: 'pending' },
    { agent: 'Strategy Agent', message: 'Waiting for research output...', status: 'pending' },
    { agent: 'Risk Agent', message: 'Waiting for signal rules...', status: 'pending' },
    { agent: 'Backtest Agent', message: 'Waiting for risk validation...', status: 'pending' },
  ])
  const [showRawLogs, setShowRawLogs] = useState(false)
  const [rawFeed, setRawFeed] = useState(data.feed)

  const wsRef = useRef<WebSocket | null>(null)
  const draftRef = useRef<HTMLDivElement | null>(null)
  /** Avoid double completion when WS and HTTP poll both see terminal state. */
  const generationDoneRef = useRef(false)
  const nlBriefRef = useRef(nlBrief)
  nlBriefRef.current = nlBrief

  // Build risk constraint text from selected profile
  const riskProfileMeta = RISK_PROFILES.find((r) => r.id === riskProfile)
  const riskConstraintText = riskProfileMeta
    ? riskProfileMeta.constraints.map((c) => `${c.label} ${c.value}`).join(', ')
    : ''

  /** @param nlHint 生成刚完成时传入概要框文案；默认载入最新策略时传 null，避免随输入框抖动重复请求 */
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

  // Scroll draft into view when result appears
  useEffect(() => {
    if (draftResult && draftRef.current) {
      draftRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [draftResult])

  // 未在生成时：默认展示矩阵中最近更新的一条策略（与 overview 中 matrix 顺序一致）
  useEffect(() => {
    if (generating) return
    if (!data.matrix?.length) {
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
      } catch {
        if (!canceled) setDraftResult(null)
      }
    })()
    return () => {
      canceled = true
    }
  }, [data.matrix, generating, buildDraftFromStrategyDetail])

  // WebSocket (live trace) + HTTP poll (reliable draft — pipeline may finish before WS connects)
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

    /** Only when strategy detail API is unavailable; WS payload rarely carries narrative fields. */
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
    }

    const finishSuccess = async (opts: { strategyId: string | null; wsDetail?: Record<string, unknown> }) => {
      if (generationDoneRef.current || closed) return
      generationDoneRef.current = true
      clearPoll()

      updateTrace('backtest', 'completed', 'Backtest completed')
      updateTrace('risk', 'completed', 'Constraints validated')
      updateTrace('running', 'completed', 'Signal rules generated')
      updateTrace('queued', 'completed', 'Market universe scanned')

      const sid = opts.strategyId
      let draftLoaded = false
      if (sid) {
        try {
          const d = await api.strategy.detail(sid)
          setDraftResult(
            buildDraftFromStrategyDetail(d, nlBriefRef.current.trim() || null)
          )
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

          if (msg.stage === 'running') updateTrace('running', 'running', 'Generating signal and rebalance rules...')
          if (msg.stage === 'risk') updateTrace('risk', 'running', 'Validating constraints...')
          if (msg.stage === 'backtest') updateTrace('backtest', 'running', 'Running backtest simulation...')

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

    // Reset trace
    setTraceItems([
      { agent: 'Research Agent', message: 'Scanning market universe...', status: 'running' },
      { agent: 'Strategy Agent', message: 'Waiting for research output...', status: 'pending' },
      { agent: 'Risk Agent', message: 'Waiting for signal rules...', status: 'pending' },
      { agent: 'Backtest Agent', message: 'Waiting for risk validation...', status: 'pending' },
    ])
    setDraftResult(null)
    setRawFeed(data.feed)
    setGenerating(true)
    setTaskProgress(0)
    setTaskStatus('queued')

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

  return (
    <div className="strategy-builder">
      {/* Left: 策略概要 */}
      <div className="builder-col builder-brief">
        <div className="builder-section-head">
          <h4 className="builder-section-title">策略概要</h4>
          <span className="builder-section-sub">描述交易想法、风控约束与目标市场</span>
        </div>

        <div className="builder-field">
          <label>市场</label>
          <div className="builder-segmented">
            {MARKETS.map((m) => (
              <button
                key={m}
                className={market === m ? 'active' : ''}
                onClick={() => setMarket(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="builder-field">
          <label>股票池</label>
          <input
            value={universe}
            onChange={(e) => setUniverse(e.target.value)}
            placeholder="例如：沪深 300、S&P 500、BTC/ETH 永续合约"
          />
        </div>

        <div className="builder-field">
          <label>策略类型</label>
          <select value={strategyStyle} onChange={(e) => setStrategyStyle(e.target.value)}>
            {STRATEGY_STYLES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="builder-field">
          <label>风险偏好</label>
          <div className="builder-risk-options">
            {RISK_PROFILES.map((r) => (
              <button
                key={r.id}
                className={`builder-risk-btn ${riskProfile === r.id ? 'active' : ''}`}
                onClick={() => setRiskProfile(r.id)}
              >
                {r.label}
              </button>
            ))}
          </div>
          {riskMeta && (
            <div className="builder-risk-constraints">
              {riskMeta.constraints.map((c, i) => (
                <div className="builder-constraint" key={i}>
                  <span>{c.label}</span>
                  <strong>{c.value}</strong>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="builder-field">
          <label>自然语言描述</label>
          <textarea
            value={nlBrief}
            onChange={(e) => setNlBrief(e.target.value)}
            rows={5}
            placeholder="例如：创建一个周频调仓的A股多因子价值策略，要求 ROE > 15%、PE 分位数 < 30%、流动性过滤、最大回撤不超过 15%、基准为沪深 300。"
            disabled={generating}
          />
        </div>

        <div className="builder-actions">
          <button className="btn builder-cta" onClick={handleGenerate} disabled={generating || !nlBrief.trim()}>
            {generating ? `生成中... ${taskProgress}%` : '生成策略草案'}
          </button>
          <button className="btn secondary" disabled={generating}>
            保存为模板
          </button>
        </div>
      </div>

      {/* Center: 策略草案 */}
      <div className="builder-col builder-draft" ref={draftRef}>
        <div className="builder-section-head">
          <h4 className="builder-section-title">策略草案</h4>
          <span className="builder-section-sub">
            {draftResult
              ? '审查策略逻辑、约束与下一步操作'
              : '生成后的策略草案将显示在此处'}
          </span>
        </div>

        {!draftResult && !generating && (
          <div className="draft-empty">
            <div className="draft-empty-icon">◈</div>
            <p>暂无策略草案</p>
            <span>从策略概要生成草案，即可查看策略逻辑、约束与下一步操作。</span>
          </div>
        )}

        {generating && !draftResult && (
          <div className="draft-generating">
            <div className="draft-generating-spinner" />
            <p>Strategy Agent 正在生成策略草案…</p>
            <span>{taskStatus || 'queued'} &middot; {taskProgress}%</span>
          </div>
        )}

        {draftResult && (
          <div className="draft-result">
            <div className="draft-header">
              <span className="draft-status">草稿</span>
              <h3 className="draft-name">{draftResult.name}</h3>
              <span className="draft-id">#{draftResult.id.slice(0, 8)}</span>
            </div>

            <div className="draft-sections">
              <div className="draft-section">
                <h5>信号定义</h5>
                <p>{draftResult.signalDefinition}</p>
              </div>
              <div className="draft-section">
                <h5>入场规则</h5>
                <p>{draftResult.entryRules}</p>
              </div>
              <div className="draft-section">
                <h5>出场规则</h5>
                <p>{draftResult.exitRules}</p>
              </div>
              <div className="draft-section">
                <h5>调仓频率</h5>
                <p>{draftResult.rebalanceFrequency}</p>
              </div>
              <div className="draft-section">
                <h5>仓位管理</h5>
                <p>{draftResult.positionSizing}</p>
              </div>
              <div className="draft-section">
                <h5>风控约束</h5>
                <p>{draftResult.riskConstraints}</p>
              </div>
              <div className="draft-section">
                <h5>基准</h5>
                <p>{draftResult.benchmark}</p>
              </div>
            </div>

            <div className="draft-next-actions">
              <span className="draft-next-label">下一步操作</span>
              <div className="draft-next-buttons">
                <button className="btn" onClick={() => void handleDraftAction('backtest')}>运行回测</button>
                <button className="btn secondary" onClick={() => void handleDraftAction('review')}>审查信号逻辑</button>
                <button className="btn secondary" onClick={() => void handleDraftAction('risk')}>风控检查</button>
                <button className="btn secondary" onClick={() => void handleDraftAction('save')}>保存草稿</button>
              </div>
              {actionNotice && <div className="draft-action-notice">{actionNotice}</div>}
            </div>
          </div>
        )}
      </div>

      {/* Right: 生成追踪 */}
      <div className="builder-col builder-trace">
        <div className="builder-section-head">
          <h4 className="builder-section-title">生成追踪</h4>
          <span className="builder-section-sub">Agent 工作流与校验节点</span>
        </div>

        <div className="trace-list">
          {traceItems.map((item, i) => (
            <div className={`trace-item trace-${item.status}`} key={i}>
              <div className="trace-dot" />
              <div className="trace-body">
                <strong>{item.agent}</strong>
                <span>{item.message}</span>
              </div>
              {item.status === 'completed' && <span className="trace-check">&#10003;</span>}
              {item.status === 'failed' && <span className="trace-cross">&#10007;</span>}
            </div>
          ))}
        </div>

        <button className="trace-toggle" onClick={() => setShowRawLogs((v) => !v)}>
          {showRawLogs ? '隐藏原始日志' : '查看原始 Agent 日志'}
        </button>

        {showRawLogs && (
          <div className="trace-raw">
            {rawFeed.slice(0, 20).map((f, i) => (
              <div className={`trace-raw-item raw-${f.tone}`} key={i}>
                <span className="trace-raw-time">{f.time}</span>
                <span className="trace-raw-agent">{f.agent}</span>
                <span className="trace-raw-event">{f.event}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
