interface MonthlyHeatmapProps {
  monthlyReturns: Record<string, number>
}

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function pct(v: number): string {
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`
}

function cellColor(v: number): string {
  const intensity = Math.min(Math.abs(v) / 0.08, 1)
  if (v >= 0) {
    const g = Math.round(79 + (240 - 79) * intensity)
    const a = 0.12 + 0.55 * intensity
    return `rgba(30, ${g}, 100, ${a})`
  }
  const r = Math.round(180 + (255 - 180) * intensity)
  const a = 0.12 + 0.55 * intensity
  return `rgba(${r}, 60, 80, ${a})`
}

export default function MonthlyHeatmap({ monthlyReturns }: MonthlyHeatmapProps) {
  if (!monthlyReturns || Object.keys(monthlyReturns).length === 0) {
    return <div className="bt-monthly-empty">无月度收益数据。运行含 IS/OOS 切分的回测后此处自动填充。</div>
  }

  const years = [...new Set(Object.keys(monthlyReturns).map((k) => k.slice(0, 4)))].sort()

  return (
    <div className="bt-monthly-heatmap">
      <div className="bt-monthly-header">
        <div className="bt-monthly-year-label" />
        {MONTH_LABELS.map((m) => (
          <div key={m} className="bt-monthly-col-label">{m}</div>
        ))}
        <div className="bt-monthly-col-label bt-monthly-ytd">YTD</div>
      </div>
      {years.map((year) => {
        let ytd = 1.0
        const cells = Array.from({ length: 12 }, (_, i) => {
          const key = `${year}-${String(i + 1).padStart(2, '0')}`
          return monthlyReturns[key] ?? null
        })
        cells.forEach((v) => { if (v !== null) ytd *= 1 + v })
        const ytdReturn = ytd - 1

        return (
          <div key={year} className="bt-monthly-row">
            <div className="bt-monthly-year-label">{year}</div>
            {cells.map((v, i) => (
              <div
                key={i}
                className={`bt-monthly-cell ${v === null ? 'empty' : ''}`}
                style={v !== null ? { background: cellColor(v) } : undefined}
                title={v !== null ? `${year}-${String(i + 1).padStart(2, '0')}: ${pct(v)}` : '无数据'}
              >
                {v !== null ? (
                  <span className={v >= 0 ? 'pos' : 'neg'}>{pct(v)}</span>
                ) : (
                  <span className="na">—</span>
                )}
              </div>
            ))}
            <div
              className="bt-monthly-cell bt-monthly-ytd-cell"
              style={{ background: cellColor(ytdReturn) }}
            >
              <span className={ytdReturn >= 0 ? 'pos' : 'neg'}>{pct(ytdReturn)}</span>
            </div>
          </div>
        )
      })}
      <div className="bt-monthly-legend">
        <div className="bt-monthly-legend-track">
          <div className="bt-monthly-legend-grad" />
          <div className="bt-monthly-legend-labels">
            <span className="neg">-8%+</span>
            <span>0</span>
            <span className="pos">+8%+</span>
          </div>
        </div>
      </div>
    </div>
  )
}
