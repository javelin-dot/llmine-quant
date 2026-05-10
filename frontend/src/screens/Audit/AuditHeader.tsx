import { useAudit } from '../../contexts/AuditContext'

interface Props {
  onModal?: (target: string) => void
}

export default function AuditHeader({ onModal }: Props) {
  const data = useAudit()
  const kpis = data.kpis

  return (
    <header className="audit-header">
      <div className="ah-head">
        <div>
          <h3 className="ah-title">审计追踪 · Audit Trail</h3>
          <p className="ah-sub">不可篡改的决策日志 · 每次 Agent 行动、工具调用、审批均可追溯</p>
        </div>
        <div className="ah-actions">
          <button className="ah-btn ghost" onClick={() => onModal?.('global')}>查看全局状态</button>
          <button className="ah-btn primary" onClick={() => onModal?.('approve')}>导出审计报告</button>
        </div>
      </div>
      <div className="ah-kpi-strip">
        {kpis.map((k, i) => (
          <div className={`ah-kpi tone-${k.tone}`} key={i}>
            <small>{k.label}</small>
            <strong>{k.value}</strong>
            <em>{k.trend}</em>
          </div>
        ))}
      </div>
    </header>
  )
}
