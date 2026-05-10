import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  pass: 'PASS',
  watch: 'WATCH',
  fail: 'FAIL',
  enforced: 'ENFORCED',
}

const STATUS_ICON: Record<string, string> = {
  pass: '✓',
  watch: '⚠',
  fail: '✕',
  enforced: '⛨',
}

export default function BiasGate() {
  const list = mock.data.biasGate
  const watchCount = list.filter((b) => b.status === 'watch').length
  const failCount = list.filter((b) => b.status === 'fail').length

  return (
    <div className="data-bias">
      <div className="db-head">
        <div>
          <h4 className="db-title">偏差与许可闸门 · Bias & License Gate</h4>
          <span className="db-sub">
            {list.length} 项检查 ·
            {watchCount > 0 && <em className="warn"> {watchCount} 注意</em>}
            {failCount > 0 && <em className="warn"> · {failCount} 失败</em>}
            {watchCount === 0 && failCount === 0 && <em className="ok"> 全部通过</em>}
          </span>
        </div>
        <button className="db-btn">查看规则</button>
      </div>

      <div className="db-list">
        {list.map((b, i) => (
          <article className={`db-item tone-${b.statusTone}`} key={i}>
            <div className="db-item-head">
              <span className={`db-pill tone-${b.statusTone}`}>
                <i>{STATUS_ICON[b.status]}</i>
                {STATUS_LABEL[b.status]}
              </span>
              <strong>{b.title}</strong>
              <code className="db-time">{b.lastCheck}</code>
            </div>
            <p className="db-desc">{b.desc}</p>
            <p className="db-note">
              <i>↳</i> {b.note}
            </p>
          </article>
        ))}
      </div>
    </div>
  )
}
