import { useRisk } from '../../contexts/RiskContext'

const DECISION_LABEL: Record<string, string> = {
  allowed: 'ALLOWED',
  denied: 'DENIED',
  approval_required: 'APPROVAL',
  modified: 'MODIFIED',
}

const DECISION_ICON: Record<string, string> = {
  allowed: '✓',
  denied: '✕',
  approval_required: '⏱',
  modified: '⇄',
}

export default function PolicyStream() {
  const data = useRisk()
  const list = data.policyStream

  const counts = list.reduce((acc, p) => {
    acc[p.decision] = (acc[p.decision] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="rk-policy">
      <div className="rk-policy-head">
        <div>
          <h4 className="rk-policy-title">Policy Engine · 实时决策流</h4>
          <span className="rk-policy-sub">
            <i className="rk-policy-live" />
            LIVE · 最近 10 笔决策 · 平均 {Math.round(list.reduce((s, p) => s + p.durationMs, 0) / list.length)}ms
          </span>
        </div>
        <div className="rk-policy-tally">
          <span className="rk-policy-pill tone-green">{counts.allowed || 0} ALLOW</span>
          <span className="rk-policy-pill tone-red">{counts.denied || 0} DENY</span>
          <span className="rk-policy-pill tone-yellow">{counts.approval_required || 0} APPROVE</span>
          <span className="rk-policy-pill tone-blue">{counts.modified || 0} MODIFY</span>
        </div>
      </div>

      <div className="rk-policy-list">
        {list.map((p, i) => (
          <div className={`rk-policy-row tone-${p.decisionTone}`} key={i}>
            <div className="rk-policy-time">
              <code>{p.time}</code>
              <em>{p.durationMs}ms</em>
            </div>
            <div className="rk-policy-agent">
              <span className="rk-policy-agent-tag">{p.agent}</span>
            </div>
            <div className="rk-policy-request">
              <strong>{p.request}</strong>
              <p>{p.reason}</p>
            </div>
            <div className="rk-policy-decision">
              <span className={`rk-policy-decision-pill tone-${p.decisionTone}`}>
                <i>{DECISION_ICON[p.decision]}</i>
                {DECISION_LABEL[p.decision]}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
