import { mock } from '../../data'

const STATUS_LABEL: Record<string, string> = {
  pass: 'PASS',
  watch: 'WATCH',
  fail: 'FAIL',
}

const STATUS_ICON: Record<string, string> = {
  pass: '✓',
  watch: '⚠',
  fail: '✕',
}

export default function PreTradeChecks() {
  const checks = mock.execution.preTradeChecks
  const allPass = checks.every((c) => c.status === 'pass')

  return (
    <div className="ex-pretrade">
      <div className="ex-pretrade-head">
        <div>
          <h4 className="ex-pretrade-title">预交易闸门 · Pre-Trade Gates</h4>
          <span className="ex-pretrade-sub">{checks.length} 项检查 · {allPass ? '全部通过' : '存在告警'}</span>
        </div>
        <span className={`ex-pretrade-badge tone-${allPass ? 'green' : 'yellow'}`}>
          <i className={`status-dot-${allPass ? 'green' : 'yellow'}`} />
          {allPass ? 'CLEAR' : 'WATCH'}
        </span>
      </div>
      <div className="ex-pretrade-list">
        {checks.map((c, i) => {
          const ratio = Math.min(c.current / c.limit, 1)
          return (
            <div className={`ex-check-row tone-${c.statusTone}`} key={i}>
              <div className="ex-check-row-head">
                <span className={`ex-check-icon icon-${c.statusTone}`}>{STATUS_ICON[c.status]}</span>
                <strong className="ex-check-name">{c.name}</strong>
                <span className={`ex-check-status tone-${c.statusTone}`}>{STATUS_LABEL[c.status]}</span>
              </div>
              <div className="ex-check-bar-wrap">
                <div className="ex-check-bar">
                  <span
                    className={`ex-check-fill fill-${c.statusTone}`}
                    style={{ width: `${ratio * 100}%` }}
                  />
                  <span
                    className="ex-check-limit"
                    style={{ left: `${(c.limit / Math.max(c.limit, c.current)) * 100}%` }}
                    title={`阈值 ${c.limit}`}
                  />
                </div>
                <div className="ex-check-numbers">
                  <span className="ex-check-current">{c.current.toFixed(2)}</span>
                  <em>/</em>
                  <span className="ex-check-limit-num">{c.limit.toFixed(2)}</span>
                </div>
              </div>
              <p className="ex-check-note">{c.note}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
