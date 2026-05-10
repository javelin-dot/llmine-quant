import { mock } from '../../data'

const SEVERITY_LABEL: Record<string, string> = {
  critical: '严重',
  high: '高',
  medium: '中',
  low: '低',
}

const STATUS_LABEL: Record<string, string> = {
  resolved: '已解决',
  ongoing: '处理中',
  review: '复核中',
}

export default function BreachHistory() {
  const list = mock.risk.breaches
  const ongoing = list.filter((b) => b.status === 'ongoing').length
  const review = list.filter((b) => b.status === 'review').length

  return (
    <div className="rk-breach">
      <div className="rk-breach-head">
        <div>
          <h4 className="rk-breach-title">违规与事件历史 · Breach Log</h4>
          <span className="rk-breach-sub">
            7d 内 {list.length} 次 ·
            {ongoing > 0 && <em className="warn"> {ongoing} 处理中</em>}
            {review > 0 && <em className="warn"> · {review} 复核</em>}
            {ongoing === 0 && review === 0 && <em className="ok"> 全部已解决</em>}
          </span>
        </div>
        <button className="rk-breach-btn">导出周报</button>
      </div>

      <div className="rk-breach-timeline">
        {list.map((b, i) => (
          <article className={`rk-breach-row severity-${b.severityTone} status-${b.status}`} key={i}>
            <div className="rk-breach-rail">
              <span className={`rk-breach-dot dot-${b.severityTone}`} />
              {i < list.length - 1 && <span className="rk-breach-line" />}
            </div>
            <div className="rk-breach-card">
              <header className="rk-breach-card-head">
                <div className="rk-breach-card-title">
                  <span className={`rk-breach-sev pill-${b.severityTone}`}>{SEVERITY_LABEL[b.severity]}</span>
                  <strong>{b.title}</strong>
                </div>
                <div className="rk-breach-meta">
                  <code>{b.time}</code>
                  <span className={`rk-breach-status pill-${b.statusTone}`}>{STATUS_LABEL[b.status]}</span>
                </div>
              </header>
              <p className="rk-breach-detail">{b.detail}</p>
              <p className="rk-breach-resolution">
                <i>↳</i> {b.resolution}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
