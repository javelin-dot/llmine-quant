import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { StrategyProvider } from '../../contexts/StrategyContext'
import LifecycleOverview from './LifecycleOverview'
import StrategyBuilder from './StrategyBuilder'
import StrategyMatrix from './StrategyMatrix'
import StrategyLifecycle from './StrategyLifecycle'
import StrategyDetailModal from './StrategyDetailModal'

interface StrategyProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Strategy({ onNavigate, onModal }: StrategyProps) {
  const [data, setData] = useState<MockData['strategy'] | null>(null)
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [lastCreatedId, setLastCreatedId] = useState<string | null>(null)
  const [stageFilter, setStageFilter] = useState<string | null>(null)

  const refresh = useCallback(() => {
    api.strategy.overview()
      .then(setData)
      .catch((e) => console.error('Strategy API error:', e))
  }, [])

  useEffect(() => {
    refresh()
  }, [])

  const handleOpenStrategy = useCallback((id: string) => {
    setSelectedStrategyId(id)
    if (id === lastCreatedId) {
      setLastCreatedId(null)
    }
  }, [lastCreatedId])

  const handleCreateOpenStrategy = useCallback((id: string) => {
    setLastCreatedId(id)
    setSelectedStrategyId(id)
  }, [])

  if (!data) return <div className="strategy-root">Loading Strategy Factory...</div>

  return (
    <StrategyProvider value={data}>
      <div className="strategy-root strategy-workspace">

        {/* ================================================================ */}
        {/* Page Header — Strategy Factory identity + system status */}
        {/* ================================================================ */}
        <header className="sf-header">
          <div className="sf-header-left">
            <div className="sf-header-brand">
              <h1 className="sf-header-title">Strategy Factory</h1>
              <span className="sf-header-divider" />
              <span className="sf-header-sub">策略研究、回测、风控与上线工作台</span>
            </div>
            <p className="sf-header-desc">
              AI 辅助策略研究、回测与上线工作流
            </p>
          </div>
          <div className="sf-header-right">
            <span className="sf-status-pill sf-status-autopilot">
              <span className="sf-status-dot sf-dot-green" />
              <span className="sf-status-label">AI Autopilot</span>
              <span className="sf-status-value">ON</span>
            </span>
            <span className="sf-status-pill sf-status-risk">
              <span className="sf-status-dot sf-dot-green" />
              <span className="sf-status-label">Risk Gate</span>
              <span className="sf-status-value">NORMAL</span>
            </span>
            <span className="sf-status-pill sf-status-market">
              <span className="sf-status-dot sf-dot-green" />
              <span className="sf-status-label">Market Data</span>
              <span className="sf-status-value">CONNECTED</span>
            </span>
            <button
              className="sf-kill-switch"
              onClick={() => onModal?.('kill')}
              title="紧急熔断 — 暂停所有实盘策略"
            >
              <span className="sf-kill-icon">◼</span>
              紧急熔断
            </button>
          </div>
        </header>

        {/* ================================================================ */}
        {/* Lifecycle Overview — stage cards with filter */}
        {/* ================================================================ */}
        <LifecycleOverview
          onFilterStage={setStageFilter}
          activeFilter={stageFilter}
        />

        {/* ================================================================ */}
        {/* Primary Workspace — 3-column: Brief | Draft | Trace */}
        {/* ================================================================ */}
        <StrategyBuilder
          onRefresh={refresh}
          onOpenStrategy={handleCreateOpenStrategy}
        />

        {/* ================================================================ */}
        {/* Strategy Matrix — portfolio & historical strategy table */}
        {/* ================================================================ */}
        <StrategyMatrix
          onNavigate={onNavigate}
          onOpenStrategy={handleOpenStrategy}
          highlightId={lastCreatedId}
          stageFilter={stageFilter}
        />

        {/* ================================================================ */}
        {/* Strategy Lifecycle — collapsed by default, bound to selection */}
        {/* ================================================================ */}
        <StrategyLifecycle strategyId={selectedStrategyId} />
      </div>

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
