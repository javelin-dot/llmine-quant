import { mock } from '../../data'

export default function PipelineRibbon() {
  const stages = mock.strategy.pipelineStatus
  const total = stages.reduce((acc, s) => acc + s.count, 0)
  return (
    <div className="pipeline-ribbon">
      {stages.map((s, i) => {
        const ratio = total > 0 ? s.count / total : 0
        return (
          <div className={`pipeline-stage stage-${s.tone}`} key={s.stage}>
            <div className="pipeline-stage-head">
              <span className="pipeline-stage-index">0{i + 1}</span>
              <span className={`pipeline-dot dot-${s.tone}`} />
            </div>
            <strong className="pipeline-stage-count">{s.count}</strong>
            <span className="pipeline-stage-label">{s.stage}</span>
            <div className="pipeline-stage-bar">
              <span style={{ width: `${Math.max(ratio * 100, 6).toFixed(1)}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
