import { useRisk } from '../../contexts/RiskContext'

export default function RiskBudgetMatrix() {
  const data = useRisk()
  const budgets = data.budgets

  return (
    <div className="rk-budget">
      <div className="rk-budget-head">
        <div>
          <h4 className="rk-budget-title">风险预算矩阵 · Risk Budget</h4>
          <span className="rk-budget-sub">8 项 · {budgets.filter((b) => b.tone !== 'green').length} 项预警</span>
        </div>
        <div className="rk-budget-legend">
          <span className="rk-legend-item tone-green"><i /> 安全</span>
          <span className="rk-legend-item tone-yellow"><i /> 注意</span>
          <span className="rk-legend-item tone-red"><i /> 临界</span>
        </div>
      </div>

      <div className="rk-budget-grid">
        {budgets.map((b, i) => {
          const pctRaw = (b.used / b.limit) * 100
          const pct = Math.min(pctRaw, 100)
          const overLimit = pctRaw > 100
          return (
            <article className={`rk-budget-row tone-${b.tone}`} key={i}>
              <div className="rk-budget-row-head">
                <strong className="rk-budget-name">{b.name}</strong>
                <div className="rk-budget-values">
                  <span className={`rk-budget-used tone-${b.tone}`}>
                    {b.used.toFixed(b.unit === '×' || b.unit === '' ? 2 : 1)}{b.unit}
                  </span>
                  <em className="rk-budget-sep">/</em>
                  <span className="rk-budget-limit">{b.limit}{b.unit}</span>
                </div>
              </div>
              <div className="rk-budget-bar-wrap">
                <div className="rk-budget-bar">
                  <span
                    className={`rk-budget-fill fill-${b.tone}`}
                    style={{ width: `${pct}%` }}
                  />
                  {overLimit && <i className="rk-budget-overflow" />}
                </div>
                <span className="rk-budget-pct">{pctRaw.toFixed(0)}%</span>
              </div>
              <p className="rk-budget-desc">{b.desc}</p>
            </article>
          )
        })}
      </div>
    </div>
  )
}
