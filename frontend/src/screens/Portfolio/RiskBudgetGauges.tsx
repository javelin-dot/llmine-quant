import { mock } from '../../data'

function Gauge({
  pct,
  limit,
  tone,
}: {
  pct: number
  limit: number
  tone: 'green' | 'yellow' | 'red' | 'blue' | 'purple'
}) {
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const dash = pct * circumference
  const limitDash = limit * circumference
  const overLimit = pct > limit
  const stroke = tone === 'green' ? '#4ff0a2' : tone === 'yellow' ? '#ffd166' : tone === 'red' ? '#ff5c7c' : tone === 'blue' ? '#42e8ff' : '#a98bff'

  return (
    <svg viewBox="0 0 100 100" className={`pf-gauge-svg ${overLimit ? 'over' : ''}`}>
      <defs>
        <linearGradient id={`gauge-grad-${tone}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={stroke} stopOpacity="1" />
          <stop offset="1" stopColor={stroke} stopOpacity="0.6" />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r={radius} stroke="rgba(255,255,255,0.06)" strokeWidth="8" fill="none" />
      <circle
        cx="50"
        cy="50"
        r={radius}
        stroke="rgba(255, 92, 124, 0.35)"
        strokeWidth="8"
        strokeDasharray={`${limitDash} ${circumference}`}
        strokeLinecap="butt"
        fill="none"
        transform="rotate(-90 50 50)"
        opacity="0.45"
      />
      <circle
        cx="50"
        cy="50"
        r={radius}
        stroke={`url(#gauge-grad-${tone})`}
        strokeWidth="8"
        strokeDasharray={`${dash} ${circumference}`}
        strokeLinecap="round"
        fill="none"
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="48" textAnchor="middle" className="pf-gauge-pct">
        {(pct * 100).toFixed(0)}
      </text>
      <text x="50" y="62" textAnchor="middle" className="pf-gauge-pct-sym">
        %
      </text>
    </svg>
  )
}

export default function RiskBudgetGauges() {
  const items = mock.portfolio.riskBudget
  return (
    <div className="pf-risk">
      <div className="pf-risk-head">
        <div>
          <h4 className="pf-risk-title">风险预算 · Risk Budget</h4>
          <span className="pf-risk-sub">实时 vs 阈值 · 红色环 = 限额</span>
        </div>
      </div>
      <div className="pf-risk-grid">
        {items.map((it, i) => {
          const overLimit = it.pct > it.limit
          return (
            <div className={`pf-risk-cell tone-${it.tone} ${overLimit ? 'warn' : ''}`} key={i}>
              <Gauge pct={it.pct} limit={it.limit} tone={it.tone} />
              <div className="pf-risk-info">
                <strong className="pf-risk-label">{it.label}</strong>
                <span className="pf-risk-meta">阈值 {(it.limit * 100).toFixed(0)}%</span>
                <p className="pf-risk-desc">{it.desc}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
