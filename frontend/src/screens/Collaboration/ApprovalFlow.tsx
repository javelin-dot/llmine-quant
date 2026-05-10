import { useCollaboration } from '../../contexts/CollaborationContext'

export default function ApprovalFlow() {
  const data = useCollaboration()
  const flow = data.approvalFlow
  const done = flow.filter((s) => s.completed).length
  const total = flow.length

  return (
    <div className="collab-flow">
      <div className="cf-head">
        <div>
          <h4 className="cf-title">上线审批流 · Approval Pipeline</h4>
          <span className="cf-sub">{done} / {total} 阶段完成 · 六方确认后自动部署</span>
        </div>
        <div className="cf-progress">
          <div className="cf-progress-bar">
            <i style={{ width: `${(done / total) * 100}%` }} />
          </div>
          <span>{Math.round((done / total) * 100)}%</span>
        </div>
      </div>
      <div className="cf-stages">
        {flow.map((s, i) => (
          <div className={`cf-stage tone-${s.tone} ${s.completed ? 'completed' : ''}`} key={i}>
            <div className="cf-stage-dot">
              {s.completed ? '✓' : i + 1}
            </div>
            <div className="cf-stage-body">
              <strong>{s.stage}</strong>
              <span className="cf-stage-assignee">{s.assignee}</span>
              <span className="cf-stage-note">{s.note}</span>
            </div>
            {i < flow.length - 1 && <div className="cf-stage-connector" />}
          </div>
        ))}
      </div>
    </div>
  )
}
