import { useRisk } from '../../contexts/RiskContext'

interface RiskHeaderProps {
  onModal?: (target: string) => void
}

export default function RiskHeader({ onModal }: RiskHeaderProps) {
  const data = useRisk()
  const h = data.header
  const kpis = data.kpis

  const score = h.healthScore
  const radius = 52
  const stroke = 9
  const circumference = 2 * Math.PI * radius
  const dash = (score / 100) * circumference
  const gap = circumference - dash

  return (
    <div className="rk-header">
      <div className="rk-health-card">
        <div className="rk-gauge-wrap">
          <svg className="rk-gauge" viewBox="0 0 140 140" width="140" height="140">
            <circle
              cx="70" cy="70" r={radius}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={stroke}
              fill="none"
            />
            <circle
              cx="70" cy="70" r={radius}
              stroke={`url(#riskGrad-${h.healthStatusTone})`}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={`${dash} ${gap}`}
              fill="none"
              transform="rotate(-90 70 70)"
            />
            <defs>
              <linearGradient id="riskGrad-green" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#4ff0a2" />
                <stop offset="100%" stopColor="#54e3c8" />
              </linearGradient>
              <linearGradient id="riskGrad-yellow" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#ffd166" />
                <stop offset="100%" stopColor="#ff9858" />
              </linearGradient>
              <linearGradient id="riskGrad-red" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#ff8aa6" />
                <stop offset="100%" stopColor="#ff5c7c" />
              </linearGradient>
              <linearGradient id="riskGrad-blue" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#7fc8ff" />
                <stop offset="100%" stopColor="#5a8cff" />
              </linearGradient>
            </defs>
          </svg>
          <div className="rk-gauge-center">
            <strong>{score}</strong>
            <small>health</small>
          </div>
        </div>
        <div className="rk-health-meta">
          <div className="rk-status-row">
            <span className={`rk-status-pill tone-${h.healthStatusTone}`}>
              <i className={`rk-status-dot pulse-${h.healthStatusTone}`} />
              {h.healthStatus}
            </span>
            <span className={`rk-kill-pill ${h.killSwitchArmed ? 'armed' : 'disarmed'}`}>
              <i className="rk-kill-dot" />
              Kill Switch {h.killSwitchArmed ? 'ARMED' : 'OFF'}
            </span>
          </div>
          <p className="rk-incident">最近事件 · {h.lastIncident}</p>
          <div className="rk-quick-stats">
            <button className="rk-quick-stat">
              <small>24h 拦截</small>
              <strong>{h.autoBlocks24h}</strong>
            </button>
            <button className="rk-quick-stat">
              <small>待审批</small>
              <strong>{h.pendingApprovals}</strong>
            </button>
            <button className="rk-quick-stat">
              <small>活跃违规</small>
              <strong className="warn">{h.activeBreaches}</strong>
            </button>
          </div>
        </div>
        <div className="rk-header-actions">
          <button className="rk-action-btn ghost">查看决策日志</button>
          <button className="rk-action-btn danger" onClick={() => onModal?.('kill')}>
            <i className="rk-kill-icon" />
            全局熔断
          </button>
        </div>
      </div>

      <div className="rk-kpi-strip">
        {kpis.map((k, i) => (
          <div className={`rk-kpi-cell tone-${k.tone}`} key={i}>
            <span className="rk-kpi-label">{k.label}</span>
            <strong className="rk-kpi-value">{k.value}</strong>
            <span className="rk-kpi-trend">{k.trend}</span>
            <span className={`rk-kpi-stripe stripe-${k.tone}`} />
          </div>
        ))}
      </div>
    </div>
  )
}
