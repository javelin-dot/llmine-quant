import { mock } from '../../data'

const STATUS_META: Record<string, { label: string; cls: string }> = {
  live: { label: 'Live', cls: 'green' },
  paper: { label: 'Paper', cls: 'yellow' },
  backtest: { label: 'Backtest', cls: 'blue' },
  draft: { label: 'Draft', cls: 'gray' },
}

interface SparklineProps {
  data: number[]
  positive: boolean
}

function Sparkline({ data, positive }: SparklineProps) {
  const w = 120
  const h = 36
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w
      const y = h - ((v - min) / range) * (h - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  const stroke = positive ? '#4ff0a2' : '#ff5c7c'
  const fill = positive ? 'rgba(79, 240, 162, 0.18)' : 'rgba(255, 92, 124, 0.18)'

  return (
    <svg className="strategy-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline
        points={`0,${h} ${points} ${w},${h}`}
        fill={fill}
        stroke="none"
      />
      <polyline points={points} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  )
}

interface StrategyGridProps {
  onNavigate?: (target: string) => void
}

export default function StrategyGrid({ onNavigate }: StrategyGridProps) {
  return (
    <div className="strategy-grid-wrapper">
      <div className="strategy-grid-head">
        <div>
          <h4 className="strategy-grid-title">Active Strategies</h4>
          <span className="strategy-grid-sub">{mock.dashboard.strategies.length} 个策略 · 实时收益</span>
        </div>
        <button className="strategy-grid-link" onClick={() => onNavigate?.('strategy')}>
          查看全部 →
        </button>
      </div>
      <div className="strategy-grid">
        {mock.dashboard.strategies.map((s) => {
          const positive = s.return >= 0
          const meta = STATUS_META[s.status]
          return (
            <button
              key={s.id}
              className="strategy-card"
              onClick={() => onNavigate?.('strategy')}
            >
              <div className="strategy-card-top">
                <span className="strategy-card-type">{s.type}</span>
                <span className={`strategy-card-status status-tag-${meta.cls}`}>
                  <span className={`status-dot-mini status-dot-${meta.cls}`} />
                  {meta.label}
                </span>
              </div>
              <strong className="strategy-card-name">{s.name}</strong>
              <div className={`strategy-card-return ${positive ? 'pos' : 'neg'}`}>
                {positive ? '▲' : '▼'} {Math.abs(s.return * 100).toFixed(1)}%
              </div>
              <Sparkline data={s.sparkline} positive={positive} />
              <span className="strategy-card-time">{s.lastSignalTime}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
