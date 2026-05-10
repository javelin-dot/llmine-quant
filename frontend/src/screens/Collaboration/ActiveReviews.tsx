import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  pending: '待评审',
  in_review: '评审中',
  approved: '已通过',
  rejected: '已驳回',
}

const DECISION_ICON: Record<string, string> = {
  approve: '✓',
  request_changes: '✎',
  pending: '◌',
}

export default function ActiveReviews() {
  const list = mock.collaboration.activeReviews

  return (
    <div className="collab-reviews">
      <div className="cr-head">
        <div>
          <h4 className="cr-title">活跃评审 · Active Reviews</h4>
          <span className="cr-sub">{list.length} 个评审任务 · 研究 / 风控 / 交易 / 合规 四方确认</span>
        </div>
      </div>
      <div className="cr-list">
        {list.map((r) => (
          <article className={`cr-row status-${r.statusTone}`} key={r.id}>
            <div className="cr-row-head">
              <div className="cr-row-title">
                <strong>{r.strategy}</strong>
                <span className="cr-ver">{r.fromVer} → {r.toVer}</span>
              </div>
              <div className="cr-row-meta">
                <span className={`cr-priority pill-${r.priorityTone}`}>{r.priority}</span>
                <span className={`cr-status pill-${r.statusTone}`}>{STATUS_LABEL[r.status]}</span>
              </div>
            </div>
            <div className="cr-reviewers">
              {r.reviewers.map((rv, i) => (
                <div className={`cr-reviewer tone-${rv.tone}`} key={i}>
                  <span className="cr-reviewer-icon">{DECISION_ICON[rv.decision]}</span>
                  <div>
                    <small>{rv.role}</small>
                    <em>{rv.decision === 'approve' ? '同意' : rv.decision === 'request_changes' ? '需修改' : '待评审'}</em>
                  </div>
                </div>
              ))}
            </div>
            <div className="cr-foot">
              <code>{r.id}</code>
              <span>{r.createdAt}</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
