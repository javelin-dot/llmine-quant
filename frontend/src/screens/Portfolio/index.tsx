import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { PortfolioProvider } from '../../contexts/PortfolioContext'
import NAVStrip from './NAVStrip'
import AllocationDonut from './AllocationDonut'
import RiskBudgetGauges from './RiskBudgetGauges'
import CorrelationMatrix from './CorrelationMatrix'
import ConcentrationBars from './ConcentrationBars'
import RebalanceActions from './RebalanceActions'

interface PortfolioProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Portfolio({ onModal }: PortfolioProps) {
  const [data, setData] = useState<MockData['portfolio'] | null>(null)

  useEffect(() => {
    api.portfolio.overview()
      .then(setData)
      .catch((e) => console.error('Portfolio API error:', e))
  }, [])

  if (!data) return <div className="portfolio-root">Loading Portfolio…</div>

  return (
    <PortfolioProvider value={data}>
      <div className="portfolio-root">
        <NAVStrip />
        <div className="portfolio-main">
          <AllocationDonut />
          <RiskBudgetGauges />
        </div>
        <CorrelationMatrix />
        <ConcentrationBars />
        <RebalanceActions onModal={onModal} />
      </div>
    </PortfolioProvider>
  )
}
