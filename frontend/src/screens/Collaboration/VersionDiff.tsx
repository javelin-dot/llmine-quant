import { mock } from '../../data'

export default function VersionDiff() {
  const diff = mock.collaboration.diff

  return (
    <div className="collab-diff">
      <div className="cd-head">
        <div>
          <h4 className="cd-title">版本 Diff · Version Comparison</h4>
          <span className="cd-sub">{diff.header} · {diff.rows.length} 项变更</span>
        </div>
      </div>
      <div className="cd-table-wrap">
        <div className="cd-row cd-header">
          <small>变更项</small>
          <small>旧值</small>
          <small>新值</small>
          <small>影响</small>
        </div>
        {diff.rows.map((d, i) => (
          <div className="cd-row" key={i}>
            <strong>{d.field}</strong>
            <span className="cd-from">{d.from}</span>
            <span className="cd-to">{d.to}</span>
            <small>{d.impact}</small>
          </div>
        ))}
      </div>
    </div>
  )
}
