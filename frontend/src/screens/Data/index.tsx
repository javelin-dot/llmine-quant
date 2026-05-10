import DataHeader from './DataHeader'
import SourceMatrix from './SourceMatrix'
import LatencyTimeline from './LatencyTimeline'
import LineageGraph from './LineageGraph'
import BiasGate from './BiasGate'
import IncidentTimeline from './IncidentTimeline'

interface DataProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Data({ onModal }: DataProps) {
  return (
    <div className="data-root">
      <DataHeader onModal={onModal} />
      <div className="data-main">
        <SourceMatrix />
        <LatencyTimeline />
      </div>
      <LineageGraph />
      <div className="data-sub">
        <BiasGate />
        <IncidentTimeline />
      </div>
    </div>
  )
}
