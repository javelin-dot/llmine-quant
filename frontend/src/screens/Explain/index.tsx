import SignalHeader from './SignalHeader'
import AttributionWaterfall from './AttributionWaterfall'
import ConfidenceRadar from './ConfidenceRadar'
import DecisionChain from './DecisionChain'
import LineageGraph from './LineageGraph'
import BiasGate from './BiasGate'
import SimilarHistory from './SimilarHistory'

interface ExplainProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Explain({ onModal }: ExplainProps) {
  return (
    <div className="explain-root">
      <SignalHeader onModal={onModal} />
      <div className="explain-main">
        <AttributionWaterfall />
        <ConfidenceRadar />
      </div>
      <DecisionChain />
      <LineageGraph />
      <div className="explain-sub">
        <BiasGate />
        <SimilarHistory />
      </div>
    </div>
  )
}
