import { mock } from '../../data'

export default function KpiStrip() {
  const kpis = mock.backtest.kpis
  return (
    <div className="bt-kpi-strip">
      {kpis.map((k, i) => (
        <div className={`bt-kpi tone-${k.tone}`} key={i}>
          <span className="bt-kpi-label">{k.label}</span>
          <strong className="bt-kpi-value">{k.value}</strong>
          <span className="bt-kpi-trend">{k.trend}</span>
          <span className={`bt-kpi-stripe stripe-${k.tone}`} />
        </div>
      ))}
    </div>
  )
}
