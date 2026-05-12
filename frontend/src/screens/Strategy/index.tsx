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
  const [workspaceMode, setWorkspaceMode] = useState<'library' | 'create'>('library')

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

  const switchWorkspaceMode = useCallback((mode: 'library' | 'create') => {
    setWorkspaceMode(mode)
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
        </header>

        <div className="sf-workspace-switch" aria-label="策略工厂工作模式">
          <button
            className={workspaceMode === 'library' ? 'active' : ''}
            onClick={() => switchWorkspaceMode('library')}
          >
            策略库
          </button>
          <button
            className={workspaceMode === 'create' ? 'active' : ''}
            onClick={() => switchWorkspaceMode('create')}
          >
            新建策略
          </button>
        </div>

        {workspaceMode === 'create' && (
          <StrategyBuilder
            onRefresh={refresh}
            onOpenStrategy={handleCreateOpenStrategy}
            onNavigate={onNavigate}
          />
        )}

        {workspaceMode === 'library' && (
          <>
            {/* ================================================================ */}
            {/* Lifecycle Overview — stage cards with filter */}
            {/* ================================================================ */}
            <LifecycleOverview
              onFilterStage={setStageFilter}
              activeFilter={stageFilter}
            />

            {/* ================================================================ */}
            {/* Strategy Matrix — directly paired with lifecycle filters */}
            {/* ================================================================ */}
            <StrategyMatrix
              onNavigate={onNavigate}
              onOpenStrategy={handleOpenStrategy}
              highlightId={lastCreatedId}
              stageFilter={stageFilter}
            />

            <StrategyLifecycle strategyId={selectedStrategyId} />
          </>
        )}
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
