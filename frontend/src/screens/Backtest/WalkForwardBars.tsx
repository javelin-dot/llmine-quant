import { useMemo } from 'react'
import { mock } from '../../data'

export default function WalkForwardBars() {
  const folds = mock.backtest.walkForward.folds
  const { maxAbs, divergentCount } = useMemo(() => {
    const all = folds.flatMap((f) => [f.isReturn, f.oosReturn])
    const m = Math.max(...all.map((v) => Math.abs(v)), 0.05)
    let div = 0
    for (const f of folds) {
      if (Math.sign(f.isReturn) !== Math.sign(f.oosReturn) || Math.abs(f.isReturn - f.oosReturn) > 0.1) {
        div += 1
      }
    }
    return { maxAbs: m, divergentCount: div }
  }, [folds])

  return (
    <div className="bt-walkforward">
      <div className="bt-walkforward-head">
        <div>
          <h4 className="bt-walkforward-title">Walk-Forward Folds</h4>
          <span className="bt-walkforward-sub">{folds.length} 折滚动 · {divergentCount} 折出现 IS/OOS 偏离</span>
        </div>
        <div className="bt-walkforward-legend">
          <span className="legend-chip is">IS</span>
          <span className="legend-chip oos">OOS</span>
        </div>
      </div>
      <div className="bt-walkforward-grid">
        {folds.map((f, i) => {
          const isPct = f.isReturn * 100
          const oosPct = f.oosReturn * 100
          const isWidth = (Math.abs(f.isReturn) / maxAbs) * 100
          const oosWidth = (Math.abs(f.oosReturn) / maxAbs) * 100
          const divergent =
            Math.sign(f.isReturn) !== Math.sign(f.oosReturn) ||
            Math.abs(f.isReturn - f.oosReturn) > 0.1
          return (
            <div className={`bt-walkforward-fold ${divergent ? 'divergent' : ''}`} key={i}>
              <div className="bt-walkforward-period">
                <strong>{f.period}</strong>
                {divergent && <span className="bt-walkforward-warn">⚠ 偏离</span>}
              </div>
              <div className="bt-walkforward-bars">
                <div className="bt-walkforward-row">
                  <span className="bt-walkforward-label">IS</span>
                  <div className="bt-walkforward-track">
                    <span
                      className={`bt-walkforward-fill is ${isPct >= 0 ? 'pos' : 'neg'}`}
                      style={{ width: `${isWidth.toFixed(1)}%` }}
                    />
                  </div>
                  <span className={`bt-walkforward-num ${isPct >= 0 ? 'pos' : 'neg'}`}>
                    {isPct >= 0 ? '+' : ''}
                    {isPct.toFixed(1)}%
                  </span>
                </div>
                <div className="bt-walkforward-row">
                  <span className="bt-walkforward-label">OOS</span>
                  <div className="bt-walkforward-track">
                    <span
                      className={`bt-walkforward-fill oos ${oosPct >= 0 ? 'pos' : 'neg'}`}
                      style={{ width: `${oosWidth.toFixed(1)}%` }}
                    />
                  </div>
                  <span className={`bt-walkforward-num ${oosPct >= 0 ? 'pos' : 'neg'}`}>
                    {oosPct >= 0 ? '+' : ''}
                    {oosPct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
