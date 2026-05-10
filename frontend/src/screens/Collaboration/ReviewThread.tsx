import { mock } from '../../data'

export default function ReviewThread() {
  const list = mock.collaboration.reviewThread

  return (
    <div className="collab-thread">
      <div className="ct-head">
        <div>
          <h4 className="ct-title">评审讨论 · Review Thread</h4>
          <span className="ct-sub">{list.length} 条意见 · 研究员 / 风控 / 交易 / 合规</span>
        </div>
      </div>
      <div className="ct-list">
        {list.map((r, i) => (
          <article className={`ct-row tone-${r.tagClass || 'gray'}`} key={i}>
            <div className="ct-avatar">
              <span>{r.role[0]}</span>
            </div>
            <div className="ct-body">
              <header className="ct-body-head">
                <strong>{r.role}</strong>
                <span className={`ct-tag pill-${r.tagClass || 'gray'}`}>{r.tag}</span>
              </header>
              <p className="ct-text">{r.text}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
