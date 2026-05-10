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
  return (
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
  )
}
