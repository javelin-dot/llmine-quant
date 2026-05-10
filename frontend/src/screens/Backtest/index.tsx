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
  return (
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
  )
}
