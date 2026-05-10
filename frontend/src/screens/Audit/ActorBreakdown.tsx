import { mock } from '../../data'

export default function ActorBreakdown() {
  const stats = mock.audit.actorStats
  const total = stats.reduce((sum, s) => sum + s.count, 0)

  return (
    <div className="audit-actors">
      <div className="aa-head">
        <div>
          <h4 className="aa-title">Actor 分布 · Action Breakdown</h4>
          <span className="aa-sub">{stats.length} 个 Actor · 24h 累计 {total} 笔</span>
        </div>
      </div>
      <div className="aa-list">
        {stats.map((s, i) => {
          const pct = (s.count / total) * 100
          return (
            <div className={`aa-row tone-${s.tone}`} key={i}>
              <div className="aa-info">
                <strong>{s.actor}</strong>
                <span className="aa-count">{s.count} 笔</span>
              </div>
              <div className="aa-bar-wrap">
                <div className="aa-bar">
                  <i style={{ width: `${pct}%` }} />
                </div>
                <span className="aa-pct">{pct.toFixed(1)}%</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
