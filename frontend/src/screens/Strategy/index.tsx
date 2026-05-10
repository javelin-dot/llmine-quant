import PipelineRibbon from './PipelineRibbon'
import AIForge from './AIForge'
import StrategyMatrix from './StrategyMatrix'
import PipelineBoard from './PipelineBoard'

interface StrategyProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Strategy({ onNavigate, onModal }: StrategyProps) {
  return (
    <div className="strategy-root">
      <PipelineRibbon />
      <AIForge onModal={onModal} />
      <StrategyMatrix onNavigate={onNavigate} />
      <PipelineBoard onNavigate={onNavigate} />
    </div>
  )
}
