import { mock } from '../../data'

const SEVERITY_LABEL: Record<string, string> = {
  critical: '严重',
  high: '高',
  medium: '中',
  low: '低',
  info: 'INFO',
}

const STATUS_LABEL: Record<string, string> = {
  resolved: '已解决',
  ongoing: '处理中',
  review: '复核中',
}

const TYPE_LABEL: Record<string, string> = {
  rotation: '轮换',
  block: '阻断',
  access: '访问',
  violation: '违规',
  audit: '审计',
}

export default function SecurityEvents() {
  const list = mock.security.events
  const ongoing = list.filter((b) => b.status === 'ongoing').length
  const review = list.filter((b) => b.status === 'review').length

  return (
    <div className="security-events">
      <div className="se-head">
        <div>
          <h4 className="se-title">安全事件 · Security Event Log</h4>
          <span className="se-sub">
            7d 内 {list.length} 笔 ·
            {ongoing > 0 && <em className="warn"> {ongoing} 处理中</em>}
            {review > 0 && <em className="warn"> · {review} 复核</em>}
            {ongoing === 0 && review === 0 && <em className="ok"> 全部已解决</em>}
          </span>
        </div>
        <button className="se-btn">导出审计报告</button>
      </div>

      <div className="se-timeline">
        {list.map((b, i) => (
          <article className={`se-row severity-${b.severityTone} status-${b.status}`} key={i}>
            <div className="se-rail">
              <span className={`se-dot dot-${b.severityTone}`} />
              {i < list.length - 1 && <span className="se-line" />}
            </div>
            <div className="se-card">
              <header className="se-card-head">
                <div className="se-card-title">
                  <span className={`se-sev pill-${b.severityTone}`}>{SEVERITY_LABEL[b.severity]}</span>
                  <span className={`se-type tone-${b.typeTone}`}>{TYPE_LABEL[b.type]}</span>
                  <strong>{b.title}</strong>
                </div>
                <div className="se-meta">
                  <code>{b.time}</code>
                  <span className={`se-status pill-${b.statusTone}`}>{STATUS_LABEL[b.status]}</span>
                </div>
              </header>
              <p className="se-detail">
                <em className="se-actor">{b.actor}</em> · {b.detail}
              </p>
              <p className="se-resolution">
                <i>↳</i> {b.resolution}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
