import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  auto: 'AI 自动',
  review: '人工复核',
  approval: '必须审批',
}

export default function HITLRules() {
  const rules = mock.audit.hitlRules

  return (
    <div className="audit-hitl">
      <div className="ahitl-head">
        <div>
          <h4 className="ahitl-title">Human-in-the-loop Rules</h4>
          <span className="ahitl-sub">{rules.length} 条规则 · 交易、风控、资金必须人工确认</span>
        </div>
      </div>
      <div className="ahitl-list">
        {rules.map((r, i) => (
          <div className={`ahitl-row status-${r.statusTone}`} key={i}>
            <div className="ahitl-info">
              <strong>{r.rule}</strong>
              <span>{r.desc}</span>
            </div>
            <span className={`ahitl-status pill-${r.statusTone}`}>
              <i />
              {STATUS_LABEL[r.status]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
