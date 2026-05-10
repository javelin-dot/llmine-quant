import { useCollaboration } from '../../contexts/CollaborationContext'

interface Props {
  onModal?: (target: string) => void
}

export default function CollaborationHeader({ onModal }: Props) {
  const data = useCollaboration()
  const kpis = data.kpis

  return (
    <header className="collab-header">
      <div className="ch-head">
        <div>
          <h3 className="ch-title">协作实验室 · Collaboration Lab</h3>
          <p className="ch-sub">策略评审、版本 Diff、A/B Testing 与上线审批流水线</p>
        </div>
        <div className="ch-actions">
          <button className="ch-btn ghost" onClick={() => onModal?.('global')}>查看全局状态</button>
          <button className="ch-btn primary" onClick={() => onModal?.('approve')}>创建评审任务</button>
        </div>
      </div>
      <div className="ch-kpi-strip">
        {kpis.map((k, i) => (
          <div className={`ch-kpi tone-${k.tone}`} key={i}>
            <small>{k.label}</small>
            <strong>{k.value}</strong>
            <em>{k.trend}</em>
          </div>
        ))}
      </div>
    </header>
  )
}
