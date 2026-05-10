import { useRisk } from '../../contexts/RiskContext'

export default function VaRPanel() {
  const data = useRisk()
  const v = data.var
  const W = 320
  const H = 96
  const padX = 8
  const values = v.history.map((h) => h.value)
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  const stepX = (W - padX * 2) / (values.length - 1)

  const points = values.map((val, i) => {
    const x = padX + i * stepX
    const y = H - 12 - ((val - min) / range) * (H - 24)
    return [x, y] as const
  })
  const path = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const areaPath = `${path} L ${points[points.length - 1][0].toFixed(1)} ${H - 4} L ${points[0][0].toFixed(1)} ${H - 4} Z`

  const peakIdx = values.indexOf(max)
  const lastIdx = values.length - 1
  const lastVal = values[lastIdx]

  const totalContrib = v.decomposition.reduce((s, d) => s + Math.abs(d.contribution), 0)

  return (
    <div className="rk-var">
      <div className="rk-var-head">
        <div>
          <h4 className="rk-var-title">VaR · Value at Risk</h4>
          <span className="rk-var-sub">Historical Sim · {(v.confidence * 100).toFixed(0)}% 置信度 · 30d 滚动</span>
        </div>
        <div className="rk-var-tabs">
          <button className="rk-var-tab active">日 VaR</button>
          <button className="rk-var-tab">周 VaR</button>
        </div>
      </div>

      <div className="rk-var-body">
        <div className="rk-var-numbers">
          <div className="rk-var-big">
            <small>当前日 VaR</small>
            <strong>{v.currency}{v.daily}K</strong>
            <em>{v.dailyPct.toFixed(2)}% NAV</em>
          </div>
          <div className="rk-var-stat-row">
            <div className="rk-var-stat">
              <small>周 VaR</small>
              <strong>{v.currency}{v.weekly}K</strong>
              <em>{v.weeklyPct.toFixed(2)}%</em>
            </div>
            <div className="rk-var-stat">
              <small>30d 峰值</small>
              <strong>{v.currency}{max}K</strong>
              <em>{v.history[peakIdx].date}</em>
            </div>
            <div className="rk-var-stat">
              <small>30d 均值</small>
              <strong>{v.currency}{Math.round(values.reduce((s, x) => s + x, 0) / values.length)}K</strong>
              <em>方差 {Math.round(Math.sqrt(values.reduce((s, x) => s + (x - values.reduce((s, x) => s + x, 0) / values.length) ** 2, 0) / values.length))}</em>
            </div>
          </div>
        </div>

        <div className="rk-var-chart-wrap">
          <svg className="rk-var-chart" viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
            <defs>
              <linearGradient id="varArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(123, 156, 255, 0.45)" />
                <stop offset="100%" stopColor="rgba(123, 156, 255, 0)" />
              </linearGradient>
            </defs>
            <path d={areaPath} fill="url(#varArea)" />
            <path d={path} stroke="#8db4ff" strokeWidth="1.6" fill="none" strokeLinejoin="round" />
            <circle cx={points[peakIdx][0]} cy={points[peakIdx][1]} r="3.2" fill="#ff5c7c" />
            <circle cx={points[lastIdx][0]} cy={points[lastIdx][1]} r="3.6" fill="#8db4ff" stroke="#0c1124" strokeWidth="1.5" />
            <text x={points[peakIdx][0]} y={points[peakIdx][1] - 6} fontSize="9" fill="#ff8aa6" textAnchor="middle">{max}K</text>
            <text x={points[lastIdx][0]} y={points[lastIdx][1] + 14} fontSize="9" fill="#8db4ff" textAnchor="end">{lastVal}K</text>
          </svg>
          <div className="rk-var-chart-axis">
            <span>{v.history[0].date}</span>
            <span>{v.history[Math.floor(values.length / 2)].date}</span>
            <span>{v.history[lastIdx].date}</span>
          </div>
        </div>
      </div>

      <div className="rk-var-decomp">
        <div className="rk-var-decomp-head">
          <span>策略级 VaR 分解</span>
          <em>共 {v.currency}{v.decomposition.reduce((s, d) => s + (d.contribution > 0 ? d.contribution : 0), 0).toFixed(0)}K 正向暴露</em>
        </div>
        <div className="rk-var-decomp-list">
          {v.decomposition.map((d, i) => {
            const absPct = (Math.abs(d.contribution) / totalContrib) * 100
            return (
              <div className={`rk-var-decomp-row tone-${d.tone}`} key={i}>
                <span className="rk-var-decomp-name">{d.strategy}</span>
                <div className="rk-var-decomp-bar">
                  <span
                    className={`rk-var-decomp-fill fill-${d.tone} ${d.contribution < 0 ? 'neg' : ''}`}
                    style={{ width: `${absPct}%` }}
                  />
                </div>
                <span className={`rk-var-decomp-val ${d.contribution < 0 ? 'pos' : ''}`}>
                  {d.contribution >= 0 ? '+' : ''}{v.currency}{d.contribution.toFixed(1)}K
                </span>
                <em className="rk-var-decomp-pct">{(d.pct * 100).toFixed(0)}%</em>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
