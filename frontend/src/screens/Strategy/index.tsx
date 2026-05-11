import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { StrategyProvider } from '../../contexts/StrategyContext'
import PipelineRibbon from './PipelineRibbon'
import AIForge from './AIForge'
import StrategyMatrix from './StrategyMatrix'
import PipelineBoard from './PipelineBoard'
import StrategyDetailModal from './StrategyDetailModal'

interface StrategyProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Strategy({ onNavigate, onModal }: StrategyProps) {
  const [data, setData] = useState<MockData['strategy'] | null>(null)
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [lastCreatedId, setLastCreatedId] = useState<string | null>(null)

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

  if (!data) return <div className="strategy-root">Loading Strategy…</div>

  return (
    <StrategyProvider value={data}>
      <div className="strategy-root">
        <PipelineRibbon />
        <AIForge onModal={onModal} onRefresh={refresh} onOpenStrategy={handleCreateOpenStrategy} />
        <StrategyMatrix
          onNavigate={onNavigate}
          onOpenStrategy={handleOpenStrategy}
          highlightId={lastCreatedId}
        />
        <PipelineBoard
          onNavigate={onNavigate}
          onOpenStrategy={handleOpenStrategy}
          highlightId={lastCreatedId}
        />
      </div>
      {selectedStrategyId && (
        <StrategyDetailModal
          key={selectedStrategyId}
          strategyId={selectedStrategyId}
          onClose={() => setSelectedStrategyId(null)}
          onChanged={refresh}
        />
      )}
    </StrategyProvider>
  )
}
