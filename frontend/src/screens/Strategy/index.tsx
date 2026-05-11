import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { StrategyProvider } from '../../contexts/StrategyContext'
import PipelineRibbon from './PipelineRibbon'
import AIForge from './AIForge'
import StrategyMatrix from './StrategyMatrix'
import PipelineBoard from './PipelineBoard'

interface StrategyProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Strategy({ onNavigate, onModal }: StrategyProps) {
  const [data, setData] = useState<MockData['strategy'] | null>(null)

  const refresh = useCallback(() => {
    api.strategy.overview()
      .then(setData)
      .catch((e) => console.error('Strategy API error:', e))
  }, [])

  useEffect(() => {
    refresh()
  }, [])

  if (!data) return <div className="strategy-root">Loading Strategy…</div>

  return (
    <StrategyProvider value={data}>
      <div className="strategy-root">
        <PipelineRibbon />
        <AIForge onModal={onModal} onRefresh={refresh} />
        <StrategyMatrix onNavigate={onNavigate} />
        <PipelineBoard onNavigate={onNavigate} />
      </div>
    </StrategyProvider>
  )
}
