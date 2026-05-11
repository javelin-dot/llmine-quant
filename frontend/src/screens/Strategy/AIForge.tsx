import { useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'
import { useStrategy } from '../../contexts/StrategyContext'

const RISK_FILTERS: { id: 'all' | 'conservative' | 'balanced' | 'aggressive'; label: string; tone: string }[] = [
  { id: 'all', label: '全部', tone: 'blue' },
  { id: 'conservative', label: '保守', tone: 'green' },
  { id: 'balanced', label: '平衡', tone: 'yellow' },
  { id: 'aggressive', label: '激进', tone: 'red' },
]

interface AIForgeProps {
  onModal?: (target: string) => void
  onRefresh?: () => void
}

export default function AIForge({ onModal, onRefresh }: AIForgeProps) {
  const data = useStrategy()
  const [prompt, setPrompt] = useState(data.nlPrompt)
  const [risk, setRisk] = useState<'all' | 'conservative' | 'balanced' | 'aggressive'>('all')
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null)

  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState(0)
  const [liveFeed, setLiveFeed] = useState(data.feed)

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!generating || !taskId) return

    let fallbackInterval: ReturnType<typeof setInterval> | null = null
    let closed = false

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

          setLiveFeed((prev) => {
            const time = msg.timestamp
              ? new Date(msg.timestamp).toLocaleTimeString('zh-CN', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })
              : '--:--:--'
            const agent = (msg.agent || 'system').replace(/^agent-/, '')
            let eventText = `[${msg.stage}] ${msg.event}`
            if (msg.stage === 'done' && msg.detail?.strategyId) {
              eventText = `策略已生成 · ${msg.detail.strategyId.slice(0, 8)}`
            } else if (msg.stage === 'failed') {
              eventText = `生成失败: ${msg.detail?.error || msg.event}`
            }
            const tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red' =
              msg.stage === 'failed'
                ? 'red'
                : msg.stage === 'done'
                  ? 'green'
                  : 'blue'
            const item = { time, agent, event: eventText, tone }
            return [item, ...prev]
          })

          if (msg.stage === 'done' || msg.stage === 'failed') {
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
          setLiveFeed(feed)
          if (task.status === 'succeeded' || task.status === 'failed') {
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

    return () => {
      closed = true
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (fallbackInterval) clearInterval(fallbackInterval)
    }
  }, [generating, taskId, onRefresh])

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setLiveFeed(data.feed)
    setGenerating(true)
    setTaskProgress(0)
    setTaskStatus('queued')
    try {
      const task = await api.strategy.createTask({
        prompt,
        market: 'A',
        riskProfile: risk === 'all' ? 'balanced' : risk,
      })
      setTaskId(task.id)
      setTaskStatus(task.status)
    } catch (e) {
      console.error('Create task error:', e)
      setGenerating(false)
    }
  }

  const filteredTemplates = data.templates.filter((t) =>
    risk === 'all' ? true : t.risk === risk
  )

  const feed = generating ? liveFeed : data.feed

  return (
    <div className="ai-forge">
      <div className="ai-forge-left">
        <div className="ai-forge-head">
          <div>
            <span className="ai-forge-eyebrow">
              <span className="ai-forge-eyebrow-dot" />
              AI Strategy Forge · 一句话生成可回测策略
            </span>
            <h2 className="ai-forge-title">告诉 AI 你的目标</h2>
          </div>
          <div className="ai-forge-shortcut">
            <kbd>⌘</kbd>
            <kbd>K</kbd>
          </div>
        </div>

        <div className="ai-forge-prompt">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            spellCheck={false}
            placeholder="例如：创建一个 BTC 趋势突破策略，最大回撤 15%，自动完成回测和模拟盘部署"
            disabled={generating}
          />
          <div className="ai-forge-prompt-foot">
            <span className="ai-forge-counter">
              {generating
                ? `${taskStatus || 'running'} · ${taskProgress}%`
                : `${prompt.length} 字符 · 7 个候选生成`}
            </span>
            <div className="ai-forge-actions">
              <button className="btn secondary" disabled={generating}>
                保存为模板
              </button>
              <button
                className="btn ai-forge-cta"
                onClick={handleGenerate}
                disabled={generating}
              >
                <span>{generating ? '◉' : '✦'}</span>
                {generating ? ' Agent 运行中…' : ' 让 Agent 开始'}
              </button>
            </div>
          </div>
        </div>

        <div className="ai-forge-filters">
          <span className="ai-forge-filter-label">风险偏好</span>
          {RISK_FILTERS.map((f) => (
            <button
              key={f.id}
              className={`ai-forge-chip chip-${f.tone} ${risk === f.id ? 'active' : ''}`}
              onClick={() => setRisk(f.id)}
              disabled={generating}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="ai-forge-templates">
          {filteredTemplates.map((t) => {
            const tone =
              t.risk === 'conservative' ? 'green' : t.risk === 'balanced' ? 'yellow' : 'red'
            return (
              <button
                key={t.id}
                className={`ai-forge-template tpl-${tone} ${activeTemplate === t.id ? 'active' : ''}`}
                onClick={() => setActiveTemplate(t.id)}
                disabled={generating}
              >
                <div className="ai-forge-template-top">
                  <span className={`ai-forge-template-tag tag-${tone}`}>{
                    t.risk === 'conservative' ? '保守' : t.risk === 'balanced' ? '平衡' : '激进'
                  }</span>
                  <span className="ai-forge-template-family">{t.family}</span>
                </div>
                <strong className="ai-forge-template-name">{t.name}</strong>
                <p className="ai-forge-template-desc">{t.desc}</p>
                <span className="ai-forge-template-market">{t.market}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="ai-forge-right">
        <div className="ai-forge-feed-head">
          <div>
            <h4 className="ai-forge-feed-title">
              <span className="ai-forge-feed-pulse" />
              Live Generation Feed
            </h4>
            <span className="ai-forge-feed-sub">Agent 决策追踪 · 实时</span>
          </div>
          <span className="ai-forge-feed-count">{feed.length}</span>
        </div>
        <div className="ai-forge-feed">
          {feed.map((f, i) => (
            <div className={`ai-forge-feed-item feed-${f.tone}`} key={i}>
              <div className="ai-forge-feed-time">{f.time}</div>
              <div className="ai-forge-feed-body">
                <span className="ai-forge-feed-agent">{f.agent}</span>
                <p className="ai-forge-feed-event">{f.event}</p>
              </div>
              <span className={`ai-forge-feed-dot dot-${f.tone}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
