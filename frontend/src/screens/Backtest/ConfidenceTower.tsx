import { mock } from '../../data'

export default function ConfidenceTower() {
  const c = mock.backtest.confidence
  const score = c.score
  const pct = Math.max(0, Math.min(1, score))
  const radius = 64
  const circumference = 2 * Math.PI * radius
  const dash = pct * circumference
  const tone = score >= 0.85 ? 'green' : score >= 0.7 ? 'yellow' : 'red'

  return (
    <div className="bt-confidence">
      <div className="bt-confidence-head">
        <h4 className="bt-confidence-title">AI Confidence</h4>
        <span className="bt-confidence-sub">数据 · 稳定性 · 滑点 · 抗压</span>
      </div>
      <div className={`bt-gauge tone-${tone}`}>
        <svg viewBox="0 0 160 160" className="bt-gauge-svg">
          <defs>
            <linearGradient id="bt-gauge-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#4c8dff" />
              <stop offset="0.5" stopColor="#42e8ff" />
              <stop offset="1" stopColor={tone === 'red' ? '#ff5c7c' : tone === 'yellow' ? '#ffd166' : '#4ff0a2'} />
            </linearGradient>
          </defs>
          <circle cx="80" cy="80" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke="url(#bt-gauge-grad)"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash.toFixed(2)} ${circumference.toFixed(2)}`}
            transform="rotate(-90 80 80)"
          />
        </svg>
        <div className="bt-gauge-label">
          <strong>{c.label}</strong>
          <span>综合置信</span>
        </div>
      </div>
      <div className="bt-confidence-list">
        {c.features.map((f, i) => (
          <div className={`bt-confidence-item tone-${f.tone}`} key={i}>
            <div className="bt-confidence-item-head">
              <strong>{f.title}</strong>
              <span className={`bt-confidence-score tone-${f.tone}`}>{f.score}</span>
            </div>
            <p>{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
