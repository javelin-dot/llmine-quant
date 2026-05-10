import { usePortfolio } from '../../contexts/PortfolioContext'

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="pf-conc-bar">
      <span style={{ width: `${pct * 100}%`, background: color }} />
    </div>
  )
}

export default function ConcentrationBars() {
  const data = usePortfolio()
  const c = data.concentration
  const sectorMax = Math.max(...c.sectors.map((s) => s.weight))
  const holdingMax = Math.max(...c.holdings.map((h) => h.weight))
  const factorMax = Math.max(...c.factors.map((f) => Math.abs(f.exposure)))

  return (
    <div className="pf-concentration">
      <div className="pf-conc-head">
        <div>
          <h4 className="pf-conc-title">集中度暴露 · Concentration</h4>
          <span className="pf-conc-sub">行业 · 重仓 · 因子</span>
        </div>
      </div>
      <div className="pf-conc-grid">
        {/* Sectors */}
        <div className="pf-conc-col">
          <div className="pf-conc-col-head">
            <span>行业暴露</span>
            <em>Top {c.sectors.length}</em>
          </div>
          <div className="pf-conc-list">
            {c.sectors.map((s) => (
              <div className="pf-conc-row" key={s.name}>
                <div className="pf-conc-row-head">
                  <strong>{s.name}</strong>
                  <span className={`pf-conc-change ${s.change >= 0 ? 'pos' : 'neg'}`}>
                    {s.change >= 0 ? '▲' : '▼'} {Math.abs(s.change * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="pf-conc-row-body">
                  <Bar pct={s.weight / sectorMax} color="#4c8dff" />
                  <span className="pf-conc-weight">{(s.weight * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Holdings */}
        <div className="pf-conc-col">
          <div className="pf-conc-col-head">
            <span>重仓持股</span>
            <em>Top {c.holdings.length}</em>
          </div>
          <div className="pf-conc-list">
            {c.holdings.map((h) => (
              <div className="pf-conc-row" key={h.symbol}>
                <div className="pf-conc-row-head">
                  <strong>{h.name}</strong>
                  <code className="pf-conc-sym">{h.symbol}</code>
                  <span className={`pf-conc-change ${h.change >= 0 ? 'pos' : 'neg'}`}>
                    {h.change >= 0 ? '▲' : '▼'} {Math.abs(h.change * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="pf-conc-row-body">
                  <Bar pct={h.weight / holdingMax} color="#42e8ff" />
                  <span className="pf-conc-weight">{(h.weight * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Factors */}
        <div className="pf-conc-col">
          <div className="pf-conc-col-head">
            <span>因子暴露</span>
            <em>Beta · 风格</em>
          </div>
          <div className="pf-conc-list">
            {c.factors.map((f) => {
              const colorMap: Record<string, string> = {
                green: '#4ff0a2',
                yellow: '#ffd166',
                red: '#ff5c7c',
                blue: '#4c8dff',
                purple: '#a98bff',
              }
              return (
                <div className="pf-conc-row" key={f.name}>
                  <div className="pf-conc-row-head">
                    <strong>{f.name}</strong>
                    <span className={`pf-conc-change ${f.exposure >= 0 ? 'pos' : 'neg'}`}>
                      {f.exposure >= 0 ? '+' : ''}
                      {f.exposure.toFixed(2)}
                    </span>
                  </div>
                  <div className="pf-conc-row-body">
                    <div className="pf-conc-bar pf-factor-bar">
                      <span className="pf-factor-zero" />
                      <span
                        className={`pf-factor-fill ${f.exposure >= 0 ? 'pos' : 'neg'}`}
                        style={{
                          width: `${(Math.abs(f.exposure) / factorMax) * 50}%`,
                          background: colorMap[f.tone],
                          [f.exposure >= 0 ? 'left' : 'right']: '50%',
                        } as React.CSSProperties}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
