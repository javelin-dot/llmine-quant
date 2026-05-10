import { useData } from '../../contexts/DataContext'

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

const TYPE_LABEL: Record<string, string> = {
  latency: '延迟',
  missing: '缺失',
  drift: '漂移',
  license: '许可',
  outage: '中断',
  schema: 'Schema',
}

export default function IncidentTimeline() {
  const data = useData()
  const list = data.incidents
  const ongoing = list.filter((b) => b.status === 'ongoing').length
  const review = list.filter((b) => b.status === 'review').length

  return (
    <div className="data-incident">
      <div className="di-head">
        <div>
          <h4 className="di-title">数据事件 · Data Incident Log</h4>
          <span className="di-sub">
            7d 内 {list.length} 笔 ·
            {ongoing > 0 && <em className="warn"> {ongoing} 处理中</em>}
            {review > 0 && <em className="warn"> · {review} 复核</em>}
            {ongoing === 0 && review === 0 && <em className="ok"> 全部已解决</em>}
          </span>
        </div>
        <button className="di-btn">导出周报</button>
      </div>

      <div className="di-timeline">
        {list.map((b, i) => (
          <article className={`di-row severity-${b.severityTone} status-${b.status}`} key={i}>
            <div className="di-rail">
              <span className={`di-dot dot-${b.severityTone}`} />
              {i < list.length - 1 && <span className="di-line" />}
            </div>
            <div className="di-card">
              <header className="di-card-head">
                <div className="di-card-title">
                  <span className={`di-sev pill-${b.severityTone}`}>{SEVERITY_LABEL[b.severity]}</span>
                  <span className={`di-type tone-${b.typeTone}`}>{TYPE_LABEL[b.type]}</span>
                  <strong>{b.title}</strong>
                </div>
                <div className="di-meta">
                  <code>{b.time}</code>
                  <span className={`di-status pill-${b.statusTone}`}>{STATUS_LABEL[b.status]}</span>
                </div>
              </header>
              <p className="di-detail">
                <em className="di-source">{b.source}</em> · {b.detail}
              </p>
              <p className="di-resolution">
                <i>↳</i> {b.resolution}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
