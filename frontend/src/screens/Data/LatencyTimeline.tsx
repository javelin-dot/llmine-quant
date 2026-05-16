import { useData } from '../../contexts/DataContext'

const W = 360
const H = 220
const PAD_L = 36
const PAD_R = 12
const PAD_T = 16
const PAD_B = 28

const IW_BAR = 360
const H_BAR = 160
const PB_L = 40
const PB_R = 12
const PB_T = 20
const PB_B = 32

export default function LatencyTimeline() {
  const data = useData()
  const t = data.latencyTrend
  const ingest = data.ingestTrend

  const nPts = Math.max(t.research.length, t.paper.length, t.live.length, t.times.length, 1)
  const denom = Math.max(nPts - 1, 1)
  const all = [...t.research, ...t.paper, ...t.live]
  const maxV = Math.max(all.length ? Math.max(...all) : 0, t.slaMs * 1.2, 1)
  const innerW = W - PAD_L - PAD_R
  const innerH = H - PAD_T - PAD_B

  const xAt = (i: number) => PAD_L + (i / denom) * innerW

  const points = (arr: number[]) =>
    arr
      .map((v, i) => {
        const x = xAt(i)
        const y = PAD_T + innerH - (v / maxV) * innerH
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')

  const slaY = PAD_T + innerH - (t.slaMs / maxV) * innerH

  const yTicks = [0, maxV * 0.5, maxV].map((v) => ({
    label: `${Math.round(v)}ms`,
    y: PAD_T + innerH - (v / maxV) * innerH,
  }))

  const ingestDates = ingest.dates ?? []
  const ingestBars = ingest.bars ?? []
  const ingN = Math.min(ingestDates.length, ingestBars.length)
  const showIngest = ingN > 0
  const maxBars = showIngest ? Math.max(...ingestBars.slice(0, ingN), 1) : 1
  const innerBw = IW_BAR - PB_L - PB_R
  const innerBh = H_BAR - PB_T - PB_B
  const barGap = ingN ? Math.min(14, innerBw / ingN * 0.35) : 0
  const barW = ingN ? Math.max(4, (innerBw - barGap * (ingN - 1)) / ingN) : 0

  const safeAvg = (arr: number[]) => (arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0)
  const ingSliceBars = ingestBars.slice(0, ingN)

  return (
    <div className="data-latency">
      <div className="dl-head">
        <div>
          <h4 className="dl-title">链路延迟（由入库节奏近似）</h4>
          <span className="dl-sub">三层相对曲线 · SLA {t.slaMs}ms · 数据源真实指标见上方矩阵</span>
        </div>
        <div className="dl-legend">
          <span className="dl-leg tone-red">
            <i /> Live <em>{t.live[t.live.length - 1] ?? '—'}ms</em>
          </span>
          <span className="dl-leg tone-yellow">
            <i /> Paper <em>{t.paper[t.paper.length - 1] ?? '—'}ms</em>
          </span>
          <span className="dl-leg tone-blue">
            <i /> Research <em>{t.research[t.research.length - 1] ?? '—'}ms</em>
          </span>
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

          {yTicks.map((tk, i) => (
            <g key={i}>
              <line x1={PAD_L} x2={W - PAD_R} y1={tk.y} y2={tk.y} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 4" />
              <text x={PAD_L - 6} y={tk.y + 3} fontSize="9" fill="rgba(255,255,255,0.42)" textAnchor="end">
                {tk.label}
              </text>
            </g>
          ))}

          <line x1={PAD_L} x2={W - PAD_R} y1={slaY} y2={slaY} stroke="rgba(255,122,133,0.4)" strokeDasharray="4 3" strokeWidth="1" />
          <text x={W - PAD_R - 4} y={slaY - 4} fontSize="9" fill="rgba(255,122,133,0.7)" textAnchor="end">
            SLA {t.slaMs}ms
          </text>

          {t.research.length > 1 && (
            <polygon points={`${PAD_L},${PAD_T + innerH} ${points(t.research)} ${W - PAD_R},${PAD_T + innerH}`} fill="url(#dl-grad-research)" />
          )}
          {t.research.length > 0 && <polyline points={points(t.research)} fill="none" stroke="#7cc6ff" strokeWidth="1.5" />}

          {t.paper.length > 1 && (
            <polygon points={`${PAD_L},${PAD_T + innerH} ${points(t.paper)} ${W - PAD_R},${PAD_T + innerH}`} fill="url(#dl-grad-paper)" />
          )}
          {t.paper.length > 0 && <polyline points={points(t.paper)} fill="none" stroke="#f9c74f" strokeWidth="1.5" />}

          {t.live.length > 1 && (
            <polygon points={`${PAD_L},${PAD_T + innerH} ${points(t.live)} ${W - PAD_R},${PAD_T + innerH}`} fill="url(#dl-grad-live)" />
          )}
          {t.live.length > 0 && <polyline points={points(t.live)} fill="none" stroke="#ff7a85" strokeWidth="1.6" />}

          {t.times.map((tm, i) => {
            if ((i % 3 !== 0 && i !== t.times.length - 1) || t.times.length === 0) return null
            const x = xAt(i)
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
          <strong>{safeAvg(t.live)}ms</strong>
        </div>
        <div className="dl-stat tone-yellow">
          <small>Paper 平均</small>
          <strong>{safeAvg(t.paper)}ms</strong>
        </div>
        <div className="dl-stat tone-blue">
          <small>Research 平均</small>
          <strong>{safeAvg(t.research)}ms</strong>
        </div>
      </div>

      {showIngest && (
        <>
          <div className="dl-head dl-ingest-head">
            <div>
              <h4 className="dl-title">本地入库体量（按交易日）</h4>
              <span className="dl-sub">recent trade_date · OHLCV 行聚合</span>
            </div>
          </div>
          <div className="dl-chart dl-ingest-chart">
            <svg viewBox={`0 0 ${IW_BAR} ${H_BAR}`} width="100%" height={H_BAR} preserveAspectRatio="none">
              {Array.from({ length: ingN }, (_, i) => {
                const d = ingestDates[i]
                const hRaw = innerBh * (ingSliceBars[i] / maxBars)
                const bx = PB_L + i * (barW + barGap)
                const top = PB_T + innerBh - hRaw
                return (
                  <g key={i}>
                    <rect x={bx} y={top} width={barW} height={hRaw} rx={3} fill="rgba(61,214,140,0.35)" stroke="rgba(61,214,140,0.55)" strokeWidth="0.8" />
                    <text
                      x={bx + barW / 2}
                      y={H_BAR - 6}
                      fontSize="9"
                      fill="rgba(255,255,255,0.48)"
                      textAnchor="middle"
                    >
                      {d.length > 8 ? d.slice(5) : d}
                    </text>
                  </g>
                )
              })}
              <text x={PB_L - 8} y={PB_T + 8} fontSize="9" fill="rgba(255,255,255,0.4)" textAnchor="end">
                bars
              </text>
              <text x={IW_BAR / 2} y={12} fontSize="9" fill="rgba(255,255,255,0.45)" textAnchor="middle">
                peak {Math.max(...ingSliceBars).toLocaleString()} / 最小 {Math.min(...ingSliceBars).toLocaleString()}
              </text>
            </svg>
          </div>
        </>
      )}
    </div>
  )
}
