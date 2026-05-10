import { useExplain } from '../../contexts/ExplainContext'

const STATUS_LABEL: Record<string, string> = {
  pass: '通过',
  watch: '观察',
  fail: '失败',
  enforced: '强制',
}

const STATUS_TONE: Record<string, 'green' | 'yellow' | 'red' | 'purple'> = {
  pass: 'green',
  watch: 'yellow',
  fail: 'red',
  enforced: 'purple',
}

export default function BiasGate() {
  const data = useExplain()
  const checks = data.biasGate
  return (
    <div className="ex-bias">
      <div className="ex-bias-head">
        <div>
          <h4 className="ex-bias-title">偏差闸门 · Bias Gate</h4>
          <span className="ex-bias-sub">幸存者 · 未来函数 · 泄漏 · 许可</span>
        </div>
        <span className="ex-bias-summary">
          {checks.filter((c) => c.status === 'pass').length}/{checks.length} 通过
        </span>
      </div>
      <ul className="ex-bias-list">
        {checks.map((c, i) => {
          const tone = STATUS_TONE[c.status]
          return (
            <li key={i} className={`ex-bias-row tone-${tone}`}>
              <span className={`ex-bias-icon icon-${tone}`}>
                {c.status === 'pass' ? '✓' : c.status === 'watch' ? '⚠' : c.status === 'fail' ? '✕' : '⚡'}
              </span>
              <div className="ex-bias-body">
                <strong>{c.check}</strong>
                <p>{c.desc}</p>
              </div>
              <span className={`ex-bias-tag tag-${tone}`}>{STATUS_LABEL[c.status]}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
