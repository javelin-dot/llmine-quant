import { useSecurity } from '../../contexts/SecurityContext'

interface Props {
  onModal?: (target: string) => void
}

export default function SecurityHeader({ onModal }: Props) {
  const data = useSecurity()
  const h = data.header
  const kpis = data.kpis

  // SVG gauge math (radius 52, stroke 9)
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const dash = (h.healthScore / 100) * circumference
  const gap = circumference - dash

  return (
    <header className="security-header">
      <div className="sh-grid">
        <div className="sh-health">
          <div className="sh-gauge">
            <div className="sh-gauge-ring">
              <svg viewBox="0 0 140 140" width="140" height="140" aria-hidden="true">
                <defs>
                  <linearGradient id="sh-grad-green" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#3dd68c" />
                    <stop offset="100%" stopColor="#0fb46a" />
                  </linearGradient>
                  <linearGradient id="sh-grad-yellow" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#f9c74f" />
                    <stop offset="100%" stopColor="#e8a319" />
                  </linearGradient>
                  <linearGradient id="sh-grad-red" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#ff7a85" />
                    <stop offset="100%" stopColor="#e23952" />
                  </linearGradient>
                  <linearGradient id="sh-grad-blue" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#7cc6ff" />
                    <stop offset="100%" stopColor="#3a8de8" />
                  </linearGradient>
                </defs>
                <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="9" />
                <circle
                  cx="70"
                  cy="70"
                  r={radius}
                  fill="none"
                  stroke={`url(#sh-grad-${h.healthStatusTone})`}
                  strokeWidth="9"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${gap}`}
                  transform="rotate(-90 70 70)"
                />
              </svg>
              <div className="sh-gauge-text">
                <strong>{h.healthScore}</strong>
              </div>
            </div>
            <span className={`sh-gauge-status tone-${h.healthStatusTone}`}>{h.healthStatus}</span>
          </div>
          <div className="sh-health-meta">
            <h3 className="sh-title">资金安全中心 · Funds Security</h3>
            <p className="sh-sub">
              <span>{h.plaintextLeaks === 0 ? '0 明文泄露' : `${h.plaintextLeaks} 明文泄露`}</span>
              <em> · </em>
              <span>24h {h.aiViolations24h} 越权拦截</span>
            </p>
            <div className="sh-pills">
              <span className={`sh-pill ${h.vaultArmed ? 'pill-green' : 'pill-red'}`}>
                <i />
                Vault {h.vaultArmed ? 'ARMED' : 'DISARMED'}
              </span>
              <span className={`sh-pill ${h.withdrawalEnabled ? 'pill-red' : 'pill-green'}`}>
                <i />
                Withdrawal {h.withdrawalEnabled ? 'ON' : 'OFF'}
              </span>
              <span className="sh-pill pill-blue">
                <i />
                轮换 {h.lastRotation}
              </span>
              <span className="sh-pill pill-yellow">
                <i />
                临期 {h.keyExpiringIn}
              </span>
            </div>
          </div>
          <div className="sh-actions">
            <button className="sh-btn ghost" onClick={() => onModal?.('global')}>AI 权限审计</button>
            <button className="sh-btn primary" onClick={() => onModal?.('approve')}>密钥轮换</button>
          </div>
        </div>
      </div>

      <div className="sh-kpi-strip">
        {kpis.map((k, i) => (
          <div className={`sh-kpi tone-${k.tone}`} key={i}>
            <small>{k.label}</small>
            <strong>{k.value}</strong>
            <em>{k.trend}</em>
          </div>
        ))}
      </div>
    </header>
  )
}
