import { useMemo } from 'react'
import { mock } from '../../data'

export default function ParameterHeatmap() {
  const heatmap = mock.backtest.parameterHeatmap
  const { min, max } = useMemo(() => {
    const flat = heatmap.cells.flat()
    return { min: Math.min(...flat), max: Math.max(...flat) }
  }, [heatmap])

  const range = max - min || 1
  const bestSharpe = heatmap.cells[heatmap.bestY][heatmap.bestX]
  const bestX = heatmap.xTicks[heatmap.bestX]
  const bestY = heatmap.yTicks[heatmap.bestY]

  return (
    <div className="bt-heatmap">
      <div className="bt-heatmap-head">
        <div>
          <h4 className="bt-heatmap-title">Parameter Sensitivity</h4>
          <span className="bt-heatmap-sub">
            Sharpe Ratio · {heatmap.xLabel} × {heatmap.yLabel}
          </span>
        </div>
        <div className="bt-heatmap-best">
          <span>最佳</span>
          <strong>{bestSharpe.toFixed(2)}</strong>
          <em>
            {heatmap.xLabel.split(' ')[0]} {bestX} · {heatmap.yLabel.split(' ')[0]} {bestY}
          </em>
        </div>
      </div>
      <div className="bt-heatmap-body">
        <div className="bt-heatmap-yaxis">
          <span className="bt-heatmap-axis-label">{heatmap.yLabel}</span>
          {heatmap.yTicks
            .map((t, i) => ({ t, i }))
            .reverse()
            .map(({ t, i }) => (
              <span key={i} className="bt-heatmap-ytick">
                {t}
              </span>
            ))}
        </div>
        <div className="bt-heatmap-grid">
          {heatmap.cells
            .map((row, y) => ({ row, y }))
            .reverse()
            .map(({ row, y }) => (
              <div className="bt-heatmap-row" key={y}>
                {row.map((cell, x) => {
                  const intensity = (cell - min) / range
                  const isBest = x === heatmap.bestX && y === heatmap.bestY
                  const tone = intensity >= 0.7 ? 'hot' : intensity >= 0.45 ? 'mid' : 'cool'
                  return (
                    <div
                      key={x}
                      className={`bt-heatmap-cell tone-${tone} ${isBest ? 'best' : ''}`}
                      style={{ '--intensity': intensity.toFixed(2) } as React.CSSProperties}
                      title={`Sharpe ${cell.toFixed(2)}`}
                    >
                      <span className="bt-heatmap-val">{cell.toFixed(2)}</span>
                      {isBest && <span className="bt-heatmap-best-dot" />}
                    </div>
                  )
                })}
              </div>
            ))}
        </div>
      </div>
      <div className="bt-heatmap-xaxis">
        <span className="bt-heatmap-axis-label">{heatmap.xLabel}</span>
        <div className="bt-heatmap-xticks">
          {heatmap.xTicks.map((t, i) => (
            <span key={i}>{t}</span>
          ))}
        </div>
      </div>
      <div className="bt-heatmap-legend">
        <span>低</span>
        <div className="bt-heatmap-gradient" />
        <span>高</span>
      </div>
    </div>
  )
}
