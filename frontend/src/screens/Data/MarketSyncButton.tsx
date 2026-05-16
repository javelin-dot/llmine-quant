import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type MarketSyncPhase, type MarketSyncStartPayload, type MarketSyncStatus } from '../../lib/api'

const PHASE_LABEL: Record<MarketSyncPhase, string> = {
  idle: '空闲',
  scanning: '扫描全市场',
  syncing: '同步行情',
  retrying: '重试失败标的',
  st_flags: '更新 ST 标记',
  completed: '已完成',
  failed: '失败',
}

const PHASE_TONE: Record<MarketSyncPhase, string> = {
  idle: 'gray',
  scanning: 'blue',
  syncing: 'blue',
  retrying: 'yellow',
  st_flags: 'blue',
  completed: 'green',
  failed: 'red',
}

const POLL_MS = 1500

function fmtEta(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec)) return '—'
  if (sec < 60) return `${Math.round(sec)}s`
  return `${(sec / 60).toFixed(1)}min`
}

function fmtElapsedSec(s: number): string {
  if (!Number.isFinite(s) || s < 0) return '0s'
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
  return `${(s / 3600).toFixed(1)}h`
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

interface Props {
  onChanged?: () => void
}

export default function MarketSyncButton({ onChanged }: Props) {
  const [status, setStatus] = useState<MarketSyncStatus | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const onChangedRef = useRef(onChanged)
  const pollingRef = useRef(false)
  const stoppedRef = useRef(false)
  const prevDoneRef = useRef(-1)
  const prevPhaseRef = useRef<MarketSyncPhase | null>(null)

  useEffect(() => { onChangedRef.current = onChanged }, [onChanged])

  const refresh = useCallback(async () => {
    try {
      const s = await api.data.syncStatus()
      setStatus(s)
      return s
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return null
    }
  }, [])

  const startPolling = useCallback(() => {
    if (pollingRef.current) return
    pollingRef.current = true

    const tick = async () => {
      if (stoppedRef.current) { pollingRef.current = false; return }
      const s = await refresh()
      if (stoppedRef.current) { pollingRef.current = false; return }
      if (!s) { pollingRef.current = false; return }

      const prevPhase = prevPhaseRef.current
      const prevDone = prevDoneRef.current
      const justFinished = (s.phase === 'completed' || s.phase === 'failed') && prevPhase && prevPhase !== s.phase
      const bumpedDone = s.done > 0 && Math.floor(s.done / 50) !== Math.floor(prevDone / 50)
      if (justFinished || bumpedDone) onChangedRef.current?.()
      prevDoneRef.current = s.done
      prevPhaseRef.current = s.phase

      if (s.isRunning) {
        window.setTimeout(() => { void tick() }, POLL_MS)
      } else {
        pollingRef.current = false
      }
    }
    void tick()
  }, [refresh])

  // mount: 初次拉状态; 若已在跑 (页面刷新场景) 立即启动轮询
  useEffect(() => {
    stoppedRef.current = false
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh().then((s) => {
      if (cancelled) return
      if (s?.isRunning) startPolling()
    })
    return () => {
      cancelled = true
      stoppedRef.current = true
    }
  }, [refresh, startPolling])

  // elapsed 计时器: running 时每秒刷新一次,即使后端轮询是 1.5s,UI 仍然每秒在动
  useEffect(() => {
    if (!status?.isRunning) return
    const id = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [status?.isRunning])

  const trigger = useCallback(async (payload: MarketSyncStartPayload = {}) => {
    setSubmitting(true)
    setError(null)
    try {
      const s = await api.data.triggerSync(payload)
      setStatus(s)
      if (s.isRunning) startPolling()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSubmitting(false)
    }
  }, [startPolling])

  if (!status) {
    return (
      <section className="market-sync">
        <div className="ms-row-loading">读取同步状态中…</div>
      </section>
    )
  }

  const phase = status.phase
  const tone = PHASE_TONE[phase]
  const isRunning = status.isRunning
  const hasResult = phase === 'completed' || phase === 'failed'
  const isScanning = phase === 'scanning'
  const progressPct = status.total > 0 ? Math.round((status.done / status.total) * 100) : 0
  const elapsedSec = status.startedAt
    ? Math.max(0, (nowMs - new Date(status.startedAt).getTime()) / 1000)
    : 0

  return (
    <section className={`market-sync tone-${tone}`}>
      <div className="ms-head">
        <div className="ms-head-title">
          <h4>
            <i className={`ms-dot tone-${tone} ${isRunning ? 'pulse' : ''}`} />
            实时行情同步 · Full Market Sync
          </h4>
          <span className="ms-sub">
            首次空库 = 全量拉取 (5000+ 只 · ~15 min) · 后续按交易日增量
          </span>
        </div>
        <div className="ms-head-actions">
          {!isRunning && (
            <button
              className="ms-btn primary"
              disabled={submitting}
              onClick={() => void trigger({})}
              title="同步范围: 默认 5 年; 已入库的标的只补齐至今"
            >
              {submitting ? <><span className="ms-spinner" /> 启动中…</> : (hasResult ? '↻ 再次同步' : '▶ 开始同步')}
            </button>
          )}
          {isRunning && (
            <span className="ms-running-badge">
              <span className="ms-spinner" />
              同步进行中 · 已运行 {fmtElapsedSec(elapsedSec)}
            </span>
          )}
          <button className="ms-btn ghost" onClick={() => setExpanded((v) => !v)}>
            {expanded ? '收起' : '详情'}
          </button>
        </div>
      </div>

      {error && <div className="bt-toast bt-toast-red">{error}</div>}

      {/* Scanning 阶段: indeterminate 进度条 + 说明 (因 total 还未知) */}
      {isScanning && (
        <div className="ms-scanning">
          <div className="ms-progress-bar indeterminate">
            <span className={`ms-progress-shimmer tone-${tone}`} />
          </div>
          <div className="ms-scanning-text">
            <strong>正在扫描全市场标的列表 …</strong>
            <span>调用 AKShare <code>stock_zh_a_spot</code> · 通常 15–25 秒</span>
          </div>
          <span className="ms-scanning-elapsed">{fmtElapsedSec(elapsedSec)}</span>
        </div>
      )}

      {/* 主进度行: total 已知后才显示 */}
      {!isScanning && (isRunning || hasResult || status.total > 0) && (
        <div className="ms-progress-row">
          <div className="ms-progress-bar">
            <div
              className={`ms-progress-fill tone-${tone}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <span className="ms-progress-text">
            <strong>{status.done.toLocaleString('en-US')}</strong>
            <em> / {status.total.toLocaleString('en-US')}</em>
            <em className="dim"> · {progressPct}%</em>
          </span>
          <span className={`ms-phase-pill tone-${tone}`}>{PHASE_LABEL[phase]}</span>
        </div>
      )}

      {/* KPI strip */}
      {(isRunning || hasResult) && (
        <div className="ms-stats">
          <div className="ms-stat">
            <small>插入</small>
            <strong>{status.insertedRows.toLocaleString('en-US')}</strong>
            <em>行</em>
          </div>
          <div className="ms-stat">
            <small>更新</small>
            <strong>{status.updatedRows.toLocaleString('en-US')}</strong>
            <em>行</em>
          </div>
          <div className={`ms-stat ${status.failures > 0 ? 'warn' : ''}`}>
            <small>失败</small>
            <strong>{status.failures}</strong>
            <em>只</em>
          </div>
          <div className="ms-stat">
            <small>跳过 (已最新)</small>
            <strong>{status.skipped.toLocaleString('en-US')}</strong>
            <em>只</em>
          </div>
          <div className="ms-stat">
            <small>速率</small>
            <strong>{status.ratePerSec.toFixed(2)}</strong>
            <em>只/s</em>
          </div>
          <div className="ms-stat">
            <small>{isRunning ? 'ETA' : '总耗时'}</small>
            <strong>
              {isRunning ? fmtEta(status.etaSeconds) : fmtElapsedSec(elapsedSec)}
            </strong>
          </div>
        </div>
      )}

      {/* 上次完成时的最近标的提示 (running 时 last_symbol 频繁变,放在 KPI 下做"流动感") */}
      {isRunning && status.lastSymbol && (
        <div className="ms-last-symbol">
          最近写入: <code>{status.lastSymbol}</code>
        </div>
      )}

      {expanded && (
        <div className="ms-detail">
          <div className="ms-detail-grid">
            <div><small>Task ID</small><code>{status.taskId ?? '—'}</code></div>
            <div><small>开始时间</small><code>{fmtTime(status.startedAt)}</code></div>
            <div><small>结束时间</small><code>{fmtTime(status.finishedAt)}</code></div>
            <div><small>最近标的</small><code>{status.lastSymbol ?? '—'}</code></div>
          </div>
          {status.error && (
            <div className="ms-error">
              <strong>失败原因:</strong>
              <pre>{status.error}</pre>
            </div>
          )}
          <div className="ms-tips">
            <p>说明:</p>
            <ul>
              <li>使用新浪 <code>stock_zh_a_daily</code> 接口 · 8 并发进程池 · 前复权 (qfq)</li>
              <li>退市/停牌标的会自动跳过 (返回空) · ST 标记同步后批量更新</li>
              <li>页面可以切走 · 后端任务独立运行 · 回来后状态自动恢复</li>
              <li>当前不会持久化任务历史; 后端进程重启 (例如 dev --reload 触发) 会丢失进度但不影响已入库数据</li>
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
