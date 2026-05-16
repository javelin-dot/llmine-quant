import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { RiskProvider } from '../../contexts/RiskContext'
import RiskHeader from './RiskHeader'
import RiskBudgetMatrix from './RiskBudgetMatrix'
import VaRPanel from './VaRPanel'
import CircuitBreakerPanel from './CircuitBreakerPanel'
import PolicyStream from './PolicyStream'
import BreachHistory from './BreachHistory'
import ComplianceGate from './ComplianceGate'

interface RiskProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Risk({ onModal }: RiskProps) {
  const [data, setData] = useState<MockData['risk'] | null>(null)

  useEffect(() => {
    api.risk.overview()
      .then(setData)
      .catch((e) => console.error('Risk API error:', e))
  }, [])

  if (!data) return <div className="risk-root">Loading Risk…</div>

  return (
    <RiskProvider value={data}>
      <div className="risk-root">
        <RiskHeader onModal={onModal} />
        <div className="risk-main">
          <RiskBudgetMatrix />
          <VaRPanel />
        </div>
        <CircuitBreakerPanel onModal={onModal} />
        <ComplianceGate />
        <div className="risk-sub">
          <PolicyStream />
          <BreachHistory />
        </div>
      </div>
    </RiskProvider>
  )
}
