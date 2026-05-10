import RiskHeader from './RiskHeader'
import RiskBudgetMatrix from './RiskBudgetMatrix'
import VaRPanel from './VaRPanel'
import CircuitBreakerPanel from './CircuitBreakerPanel'
import PolicyStream from './PolicyStream'
import BreachHistory from './BreachHistory'

interface RiskProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Risk({ onModal }: RiskProps) {
  return (
    <div className="risk-root">
      <RiskHeader onModal={onModal} />
      <div className="risk-main">
        <RiskBudgetMatrix />
        <VaRPanel />
      </div>
      <CircuitBreakerPanel onModal={onModal} />
      <div className="risk-sub">
        <PolicyStream />
        <BreachHistory />
      </div>
    </div>
  )
}
