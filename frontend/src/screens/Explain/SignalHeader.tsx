import { useExplain } from '../../contexts/ExplainContext'

interface SignalHeaderProps {
  canApprove: boolean
  busy: boolean
  onRequestApprove: () => void
  onExport: () => void
}

export default function SignalHeader({
  canApprove,
  busy,
  onRequestApprove,
  onExport,
}: SignalHeaderProps) {
  const data = useExplain()
  const h = data.signalHeader
  const actionTone = h.action === 'BUY' ? 'pos' : h.action === 'SELL' ? 'neg' : 'neutral'
  const confPct = Math.round(h.confidence * 100)

  return (
    <div className="ex-header">
      <div className="ex-header-left">
        <span className={`ex-action-pill action-${actionTone}`}>{h.action}</span>
        <div className="ex-header-target">
          <h3>{h.target}</h3>
          <span className="ex-header-meta">
            <em>{h.strategy}</em>
            <i className="ex-dot" />
            <em>{h.size}</em>
            <i className="ex-dot" />
            <em>{h.timestamp}</em>
          </span>
        </div>
      </div>
      <div className="ex-header-mid">
        <div className="ex-confidence-mini">
          <svg viewBox="0 0 64 64" className="ex-conf-ring">
            <circle cx="32" cy="32" r="26" stroke="rgba(255,255,255,0.08)" strokeWidth="6" fill="none" />
            <circle
              cx="32"
              cy="32"
              r="26"
              stroke="url(#exConfGrad)"
              strokeWidth="6"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={`${(confPct / 100) * 163.36} 163.36`}
              transform="rotate(-90 32 32)"
            />
            <defs>
              <linearGradient id="exConfGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#42e8ff" />
                <stop offset="1" stopColor="#4ff0a2" />
              </linearGradient>
            </defs>
          </svg>
          <div className="ex-conf-text">
            <strong>{confPct}</strong>
            <span>Confidence</span>
          </div>
        </div>
        <div className="ex-grade">
          <span className="ex-grade-label">Risk</span>
          <strong className="ex-grade-value">
            {h.riskGrade === '—' ? '—' : h.riskGrade.startsWith('RISK') ? h.riskGrade : `RISK ${h.riskGrade}`}
          </strong>
        </div>
        <div className="ex-trace">
          <span className="ex-trace-label">Trace</span>
          <code>{h.traceId}</code>
        </div>
      </div>
      <div className="ex-header-right">
        <span className={`ex-status-pill tone-${h.statusTone}`}>
          <i className={`ex-status-dot status-dot-${h.statusTone}`} />
          {h.status}
        </span>
        <button
          type="button"
          className="ex-header-btn primary"
          disabled={!canApprove || busy}
          onClick={onRequestApprove}
        >
          批准
        </button>
        <button type="button" className="ex-header-btn secondary" disabled={busy} onClick={onExport}>
          导出
        </button>
      </div>
    </div>
  )
}
