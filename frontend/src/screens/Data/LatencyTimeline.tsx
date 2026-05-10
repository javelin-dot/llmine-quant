import { useData } from '../../contexts/DataContext'

const W = 360
const H = 220
const PAD_L = 36
const PAD_R = 12
const PAD_T = 16
const PAD_B = 28

export default function LatencyTimeline() {
  const data = useData()
  const t = data.latencyTrend
  const all = [...t.research, ...t.paper, ...t.live]
  const maxV = Math.max(...all, t.slaMs * 1.2)
  const innerW = W - PAD_L - PAD_R
  const innerH = H - PAD_T - PAD_B

  const points = (arr: number[]) =>
    arr
      .map((v, i) => {
        const x = PAD_L + (i / (arr.length - 1)) * innerW
        const y = PAD_T + innerH - (v / maxV) * innerH
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')

  const slaY = PAD_T + innerH - (t.slaMs / maxV) * innerH

  // Y-axis ticks (3)
  const yTicks = [0, maxV * 0.5, maxV].map((v) => ({
    label: `${Math.round(v)}ms`,
    y: PAD_T + innerH - (v / maxV) * innerH,
  }))

  return (
    <div className="data-latency">
      <div className="dl-head">
        <div>
          <h4 className="dl-title">延迟时序 · 24h Latency</h4>
          <span className="dl-sub">三层 P50 中位数 · SLA {t.slaMs}ms</span>
        </div>
        <div className="dl-legend">
          <span className="dl-leg tone-red"><i /> Live <em>{t.live[t.live.length - 1]}ms</em></span>
          <span className="dl-leg tone-yellow"><i /> Paper <em>{t.paper[t.paper.length - 1]}ms</em></span>
          <span className="dl-leg tone-blue"><i /> Research <em>{t.research[t.research.length - 1]}ms</em></span>
        </div>
      </div>

      <div className="dl-chart">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none">
          <defs>
            <linearGradient id="dl-grad-research" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(124,198,255,0.32)" />
              <stop offset="100%" stopColor="rgba(124,198,255,0)" />
            </linearGradient>
            <linearGradient id="dl-grad-paper" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(249,199,79,0.28)" />
              <stop offset="100%" stopColor="rgba(249,199,79,0)" />
            </linearGradient>
            <linearGradient id="dl-grad-live" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(255,122,133,0.28)" />
              <stop offset="100%" stopColor="rgba(255,122,133,0)" />
            </linearGradient>
          </defs>

          {/* Y grid */}
          {yTicks.map((tk, i) => (
            <g key={i}>
              <line x1={PAD_L} x2={W - PAD_R} y1={tk.y} y2={tk.y} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 4" />
              <text x={PAD_L - 6} y={tk.y + 3} fontSize="9" fill="rgba(255,255,255,0.42)" textAnchor="end">{tk.label}</text>
            </g>
          ))}

          {/* SLA line */}
          <line x1={PAD_L} x2={W - PAD_R} y1={slaY} y2={slaY} stroke="rgba(255,122,133,0.4)" strokeDasharray="4 3" strokeWidth="1" />
          <text x={W - PAD_R - 4} y={slaY - 4} fontSize="9" fill="rgba(255,122,133,0.7)" textAnchor="end">SLA {t.slaMs}ms</text>

          {/* Research area + line */}
          <polygon
            points={`${PAD_L},${PAD_T + innerH} ${points(t.research)} ${W - PAD_R},${PAD_T + innerH}`}
            fill="url(#dl-grad-research)"
          />
          <polyline points={points(t.research)} fill="none" stroke="#7cc6ff" strokeWidth="1.5" />

          {/* Paper area + line */}
          <polygon
            points={`${PAD_L},${PAD_T + innerH} ${points(t.paper)} ${W - PAD_R},${PAD_T + innerH}`}
            fill="url(#dl-grad-paper)"
          />
          <polyline points={points(t.paper)} fill="none" stroke="#f9c74f" strokeWidth="1.5" />

          {/* Live area + line */}
          <polygon
            points={`${PAD_L},${PAD_T + innerH} ${points(t.live)} ${W - PAD_R},${PAD_T + innerH}`}
            fill="url(#dl-grad-live)"
          />
          <polyline points={points(t.live)} fill="none" stroke="#ff7a85" strokeWidth="1.6" />

          {/* X labels */}
          {t.times.map((tm, i) => {
            if (i % 3 !== 0 && i !== t.times.length - 1) return null
            const x = PAD_L + (i / (t.times.length - 1)) * innerW
            return (
              <text key={i} x={x} y={H - 8} fontSize="9" fill="rgba(255,255,255,0.42)" textAnchor="middle">
                {tm}
              </text>
            )
          })}
        </svg>
      </div>

      <div className="dl-stats">
        <div className="dl-stat tone-red">
          <small>Live 平均</small>
          <strong>{Math.round(t.live.reduce((a, b) => a + b, 0) / t.live.length)}ms</strong>
        </div>
        <div className="dl-stat tone-yellow">
          <small>Paper 平均</small>
          <strong>{Math.round(t.paper.reduce((a, b) => a + b, 0) / t.paper.length)}ms</strong>
        </div>
        <div className="dl-stat tone-blue">
          <small>Research 平均</small>
          <strong>{Math.round(t.research.reduce((a, b) => a + b, 0) / t.research.length)}ms</strong>
        </div>
      </div>
    </div>
  )
}
