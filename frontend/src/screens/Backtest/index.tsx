import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { BacktestProvider } from '../../contexts/BacktestContext'
import KpiStrip from './KpiStrip'
import EquityDivergence from './EquityDivergence'
import ConfidenceTower from './ConfidenceTower'
import WalkForwardBars from './WalkForwardBars'
import BacktestComparison from './BacktestComparison'
import StressScenarios from './StressScenarios'
import ParameterHeatmap from './ParameterHeatmap'

interface BacktestProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Backtest({ onNavigate }: BacktestProps) {
  const [data, setData] = useState<MockData['backtest'] | null>(null)

  useEffect(() => {
    api.backtest.overview()
      .then(setData)
      .catch((e) => console.error('Backtest API error:', e))
  }, [])

  if (!data) return <div className="backtest-root">Loading Backtest…</div>

  return (
    <BacktestProvider value={data}>
      <div className="backtest-root">
        <KpiStrip />
        <div className="backtest-main">
          <EquityDivergence />
          <ConfidenceTower />
        </div>
        <div className="backtest-sub">
          <WalkForwardBars />
          <ParameterHeatmap />
        </div>
        <BacktestComparison onNavigate={onNavigate} />
        <StressScenarios onNavigate={onNavigate} />
      </div>
    </BacktestProvider>
  )
}
