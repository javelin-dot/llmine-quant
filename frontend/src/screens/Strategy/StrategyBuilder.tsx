import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'
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
}

export default function StrategyBuilder({ onRefresh, onOpenStrategy }: StrategyBuilderProps) {
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

  // Build risk constraint text from selected profile
  const riskProfileMeta = RISK_PROFILES.find((r) => r.id === riskProfile)
  const riskConstraintText = riskProfileMeta
    ? riskProfileMeta.constraints.map((c) => `${c.label} ${c.value}`).join(', ')
    : ''

  // Scroll draft into view when result appears
  useEffect(() => {
    if (draftResult && draftRef.current) {
      draftRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [draftResult])

  // WebSocket + fallback logic
  useEffect(() => {
    if (!generating || !taskId) return

    let fallbackInterval: ReturnType<typeof setInterval> | null = null
    let fallbackTimeout: ReturnType<typeof setTimeout> | null = null
    let closed = false

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

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws/strategy-events`)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type !== 'strategy.event') return
          if (msg.taskId !== taskId) return

          setTaskStatus(msg.stage)
          setTaskProgress(msg.progress)

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

          const isDone = msg.stage === 'done' || msg.stage === 'succeeded' || msg.stage === 'completed'
          if (isDone) {
            updateTrace('backtest', 'completed', 'Backtest completed')
            updateTrace('risk', 'completed', 'Constraints validated')
            updateTrace('running', 'completed', 'Signal rules generated')
            updateTrace('queued', 'completed', 'Market universe scanned')

            setGenerating(false)
            onRefresh?.()

            const detail = msg.detail || {}
            setDraftResult({
              id: detail.strategyId || taskId,
              name: detail.strategyName || 'AI Generated Strategy',
              status: 'Draft',
              signalDefinition: detail.signalDefinition || 'Signal rules generated by Strategy Agent.',
              entryRules: detail.entryRules || 'Entry rules defined.',
              exitRules: detail.exitRules || 'Exit rules defined.',
              rebalanceFrequency: detail.rebalanceFrequency || 'Weekly',
              positionSizing: detail.positionSizing || 'Equal-weight',
              riskConstraints: riskConstraintText,
              benchmark: detail.benchmark || universe || 'CSI 300',
            })

            if (detail.strategyId) {
              onOpenStrategy?.(detail.strategyId)
            }

            if (fallbackInterval) {
              clearInterval(fallbackInterval)
              fallbackInterval = null
            }
            ws.close()
          } else if (msg.stage === 'failed' || msg.stage === 'error') {
            updateTrace('backtest', 'failed', msg.detail?.error || 'Generation failed')
            setGenerating(false)
            onRefresh?.()
            if (fallbackInterval) {
              clearInterval(fallbackInterval)
              fallbackInterval = null
            }
            ws.close()
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => {
        if (!closed && !fallbackInterval) startFallback()
      }

      ws.onclose = () => {
        wsRef.current = null
        if (!closed && generating && !fallbackInterval) startFallback()
      }
    }

    const startFallback = () => {
      fallbackInterval = setInterval(async () => {
        try {
          const task = await api.strategy.getTask(taskId)
          setTaskStatus(task.status)
          setTaskProgress(task.progress)
          const feed = await api.strategy.getFeed()
          setRawFeed(feed)

          const done = task.status === 'succeeded' || task.status === 'done' || task.status === 'completed'
          if (done) {
            updateTrace('backtest', 'completed', 'Backtest completed')
            updateTrace('risk', 'completed', 'Constraints validated')
            updateTrace('running', 'completed', 'Signal rules generated')
            updateTrace('queued', 'completed', 'Market universe scanned')
            setGenerating(false)

            setDraftResult({
              id: task.strategyId || taskId,
              name: task.strategyId ? `Strategy ${task.strategyId.slice(0, 8)}` : 'AI Generated Strategy',
              status: 'Draft',
              signalDefinition: 'Signal rules generated by Strategy Agent.',
              entryRules: 'Entry rules defined based on strategy style and universe.',
              exitRules: 'Exit when signal deteriorates or risk constraint is breached.',
              rebalanceFrequency: 'Weekly',
              positionSizing: 'Equal-weight, risk-adjusted',
              riskConstraints: riskConstraintText,
              benchmark: universe || 'CSI 300',
            })

            if (task.strategyId) {
              onOpenStrategy?.(task.strategyId)
            }
            onRefresh?.()
            if (fallbackInterval) {
              clearInterval(fallbackInterval)
              fallbackInterval = null
            }
          } else if (task.status === 'failed') {
            updateTrace('backtest', 'failed', task.error || 'Generation failed')
            setGenerating(false)
            onRefresh?.()
            if (fallbackInterval) {
              clearInterval(fallbackInterval)
              fallbackInterval = null
            }
          }
        } catch (e) {
          console.error('Fallback poll error:', e)
        }
      }, 3000)
    }

    connectWs()

    // Safety net: start fallback polling after 15s even if WebSocket is connected but stuck
    fallbackTimeout = setTimeout(() => {
      if (!closed && !fallbackInterval) {
        startFallback()
      }
    }, 15000)

    return () => {
      closed = true
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (fallbackInterval) clearInterval(fallbackInterval)
      if (fallbackTimeout) clearTimeout(fallbackTimeout)
    }
  }, [generating, taskId, onRefresh, onOpenStrategy, riskConstraintText, universe])

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
                <button className="btn">运行回测</button>
                <button className="btn secondary">审查信号逻辑</button>
                <button className="btn secondary">风控检查</button>
                <button className="btn secondary">保存草稿</button>
              </div>
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
