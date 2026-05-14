import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { StrategyProvider } from '../../contexts/StrategyContext'
import StrategyBuilder from './StrategyBuilder'
import StrategyMatrix from './StrategyMatrix'
import StrategyLifecycle from './StrategyLifecycle'
import StrategyDetailModal from './StrategyDetailModal'

interface StrategyProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

interface KpiCardProps {
  label: string
  value: string | number
  tone?: 'green' | 'yellow' | 'blue' | 'purple' | 'red' | 'default'
  sub?: string
}

function KpiCard({ label, value, tone = 'default', sub }: KpiCardProps) {
  return (
    <div className="sf2-kpi-card">
      <div className="sf2-kpi-label">{label}</div>
      <div className={`sf2-kpi-value sf2-kpi-${tone}`}>{value}</div>
      {sub && <div className="sf2-kpi-sub">{sub}</div>}
    </div>
  )
}

export default function Strategy({ onNavigate }: StrategyProps) {
  const [data, setData] = useState<MockData['strategy'] | null>(null)
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [lastCreatedId, setLastCreatedId] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const refresh = useCallback(() => {
    api.strategy.overview()
      .then(setData)
      .catch((e) => console.error('Strategy API error:', e))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const handleOpenStrategy = useCallback((id: string) => {
    setSelectedStrategyId(id)
    if (id === lastCreatedId) setLastCreatedId(null)
  }, [lastCreatedId])

  const handleCreateOpenStrategy = useCallback((id: string) => {
    setLastCreatedId(id)
    setSelectedStrategyId(id)
    setDrawerOpen(false)
  }, [])

  const kpis = useMemo(() => {
    if (!data) return null
    const matrix = data.matrix
    const liveCount = matrix.filter((r) => r.status === 'live').length
    const paperCount = matrix.filter((r) => r.status === 'paper').length
    const backtestCount = matrix.filter((r) => ['backtest', 'backtesting'].includes(r.status)).length
    const validSharpes = matrix.map((r) => r.sharpe).filter((s) => isFinite(s))
    const avgSharpe = validSharpes.length
      ? validSharpes.reduce((a, b) => a + b, 0) / validSharpes.length
      : 0
    return { total: matrix.length, liveCount, paperCount, backtestCount, avgSharpe }
  }, [data])

  if (!data) {
    return (
      <div className="strategy-root sf2-root">
        <div className="sf2-loading">Loading Strategy Factory…</div>
      </div>
    )
  }

  return (
    <StrategyProvider value={data}>
      <div className="strategy-root sf2-root">

        {/* Header */}
        <header className="sf2-header">
          <div className="sf2-header-left">
            <div className="sf2-header-title-row">
              <h1 className="sf2-title">策略工厂</h1>
              <span className="sf2-live-dot">
                <span className="status-dot-green pulseDot" />
                <span className="sf2-live-label">系统正常</span>
              </span>
            </div>
            <p className="sf2-header-sub">AI 辅助策略研究、回测与上线全流程工作台</p>
          </div>
          <div className="sf2-header-actions">
            <button
              className="sf2-btn-new"
              onClick={() => setDrawerOpen(true)}
            >
              <span>＋</span> 新建策略
            </button>
          </div>
        </header>

        {/* KPI Strip */}
        {kpis && (
          <div className="sf2-kpi-strip">
            <KpiCard label="总策略" value={kpis.total} />
            <KpiCard label="实盘运行" value={kpis.liveCount} tone="green" sub="真实资金" />
            <KpiCard label="模拟盘" value={kpis.paperCount} tone="yellow" sub="无风险验证" />
            <KpiCard label="回测中" value={kpis.backtestCount} tone="blue" sub="历史验证" />
            <KpiCard label="平均 Sharpe" value={kpis.avgSharpe.toFixed(2)} tone={kpis.avgSharpe >= 1 ? 'green' : kpis.avgSharpe >= 0.5 ? 'yellow' : 'red'} />
          </div>
        )}

        {/* Strategy Matrix with integrated filters and pagination */}
        <StrategyMatrix
          onNavigate={onNavigate}
          onOpenStrategy={handleOpenStrategy}
          highlightId={lastCreatedId}
        />

        <StrategyLifecycle strategyId={selectedStrategyId} />
      </div>

      {/* Slide-in drawer for StrategyBuilder */}
      {drawerOpen && (
        <div
          className="sf2-drawer-overlay"
          onClick={() => setDrawerOpen(false)}
        >
          <div
            className="sf2-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sf2-drawer-header">
              <span className="sf2-drawer-title">新建策略</span>
              <button
                className="sf2-drawer-close"
                onClick={() => setDrawerOpen(false)}
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
            <div className="sf2-drawer-body">
              <StrategyBuilder
                onRefresh={refresh}
                onOpenStrategy={handleCreateOpenStrategy}
                onNavigate={onNavigate}
              />
            </div>
          </div>
        </div>
      )}

      {selectedStrategyId && (
        <StrategyDetailModal
          strategyId={selectedStrategyId}
          onClose={() => setSelectedStrategyId(null)}
          onChanged={refresh}
        />
      )}
    </StrategyProvider>
  )
}
