import { useExecution } from '../../contexts/ExecutionContext'

export default function ExecutionMetrics() {
  const data = useExecution()
  const m = data.metrics
  const slip = m.slippage
  const fr = m.fillRate

  const slipMax = Math.max(...slip.buckets.map((b) => b.count))
  const totalOrders = fr.filled + fr.partial + fr.rejected + fr.canceled

  const fillData: { label: string; count: number; tone: string }[] = [
    { label: '已成交', count: fr.filled, tone: 'green' },
    { label: '部分', count: fr.partial, tone: 'yellow' },
    { label: '拒单', count: fr.rejected, tone: 'red' },
    { label: '撤单', count: fr.canceled, tone: 'gray' },
  ]

  // build a stacked donut via conic-gradient
  let cum = 0
  const stops = fillData.map((f) => {
    const start = (cum / totalOrders) * 360
    cum += f.count
    const end = (cum / totalOrders) * 360
    const color = f.tone === 'green' ? '#4ff0a2' : f.tone === 'yellow' ? '#ffd166' : f.tone === 'red' ? '#ff5c7c' : 'rgba(255,255,255,0.18)'
    return `${color} ${start.toFixed(1)}deg ${end.toFixed(1)}deg`
  }).join(', ')

  const rejectMax = Math.max(...m.rejectReasons.map((r) => r.count))

  return (
    <div className="ex-metrics">
      <div className="ex-metrics-head">
        <div>
          <h4 className="ex-metrics-title">执行质量 · Execution Quality</h4>
          <span className="ex-metrics-sub">滑点分布 · 成交率 · 拒单分类</span>
        </div>
      </div>
      <div className="ex-metrics-grid">
        {/* Slippage */}
        <section className="ex-metric-col">
          <div className="ex-metric-col-head">
            <span>滑点分布 (bp)</span>
            <em>近 50 单</em>
          </div>
          <div className="ex-slip-summary">
            <div className="ex-slip-stat">
              <small>平均</small>
              <strong className={slip.avgBps < 0 ? 'pos' : slip.avgBps > 0 ? 'neg' : ''}>
                {slip.avgBps > 0 ? '+' : ''}{slip.avgBps.toFixed(2)}bp
              </strong>
            </div>
            <div className="ex-slip-stat">
              <small>P50</small>
              <strong>{slip.p50Bps > 0 ? '+' : ''}{slip.p50Bps.toFixed(1)}bp</strong>
            </div>
            <div className="ex-slip-stat">
              <small>P95</small>
              <strong className="warn">{slip.p95Bps > 0 ? '+' : ''}{slip.p95Bps.toFixed(1)}bp</strong>
            </div>
          </div>
          <div className="ex-slip-hist">
            {slip.buckets.map((b, i) => {
              const pct = (b.count / slipMax) * 100
              const isNeg = b.range.startsWith('<') || b.range.startsWith('-')
              return (
                <div className="ex-slip-bar-col" key={i}>
                  <span
                    className={`ex-slip-bar ${isNeg ? 'pos' : 'neg'}`}
                    style={{ height: `${pct}%` }}
                  >
                    <em>{b.count}</em>
                  </span>
                  <small>{b.range}</small>
                </div>
              )
            })}
          </div>
        </section>

        {/* Fill rate */}
        <section className="ex-metric-col">
          <div className="ex-metric-col-head">
            <span>成交率 · {(fr.total * 100).toFixed(0)}%</span>
            <em>{totalOrders} 单</em>
          </div>
          <div className="ex-fill-wrap">
            <div className="ex-fill-donut" style={{ background: `conic-gradient(${stops})` }}>
              <div className="ex-fill-center">
                <strong>{(fr.total * 100).toFixed(0)}%</strong>
                <small>filled</small>
              </div>
            </div>
            <div className="ex-fill-legend">
              {fillData.map((f, i) => (
                <div className="ex-fill-row" key={i}>
                  <span className={`ex-fill-dot tone-${f.tone}`} />
                  <span className="ex-fill-label">{f.label}</span>
                  <span className="ex-fill-count">{f.count}</span>
                  <em>{((f.count / totalOrders) * 100).toFixed(0)}%</em>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Reject reasons */}
        <section className="ex-metric-col">
          <div className="ex-metric-col-head">
            <span>拒单分类</span>
            <em>{m.rejectReasons.reduce((s, r) => s + r.count, 0)} 单</em>
          </div>
          <div className="ex-reject-list">
            {m.rejectReasons.map((r, i) => {
              const pct = (r.count / rejectMax) * 100
              return (
                <div className={`ex-reject-row tone-${r.tone}`} key={i}>
                  <div className="ex-reject-row-head">
                    <strong>{r.reason}</strong>
                    <span className="ex-reject-count">{r.count}</span>
                  </div>
                  <div className="ex-reject-bar">
                    <span className={`ex-reject-fill fill-${r.tone}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}
