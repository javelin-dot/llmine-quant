import { mock } from '../../data'

function fmtCurrency(n: number, currency: string): string {
  if (currency === 'USDT' || currency === 'USD') {
    return n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(2)}M` : n >= 1000 ? `$${(n / 1000).toFixed(1)}K` : `$${n.toFixed(0)}`
  }
  return n >= 1_000_000 ? `¥${(n / 1_000_000).toFixed(2)}M` : n >= 1000 ? `¥${(n / 1000).toFixed(1)}K` : `¥${n.toFixed(0)}`
}

function fmtPct(p: number, withSign = true): string {
  const v = (p * 100).toFixed(2)
  if (!withSign) return `${v}%`
  return `${p >= 0 ? '+' : ''}${v}%`
}

export default function NAVStrip() {
  const n = mock.portfolio.nav
  const todayTone = n.todayPnl >= 0 ? 'pos' : 'neg'

  const cells: { label: string; value: string; trend?: string; tone?: 'pos' | 'neg' | 'neutral' | 'warn' }[] = [
    { label: '总市值', value: fmtCurrency(n.total, n.currency), trend: n.currency, tone: 'neutral' },
    { label: '今日 P&L', value: fmtCurrency(n.todayPnl, n.currency), trend: fmtPct(n.todayPct), tone: todayTone },
    { label: 'MTD', value: fmtPct(n.mtdPct), trend: '本月', tone: n.mtdPct >= 0 ? 'pos' : 'neg' },
    { label: 'YTD', value: fmtPct(n.ytdPct), trend: '今年', tone: n.ytdPct >= 0 ? 'pos' : 'neg' },
    { label: '现金占比', value: fmtPct(n.cashPct, false), trend: '可入场', tone: 'neutral' },
    { label: '杠杆倍数', value: `${n.leverage.toFixed(2)}x`, trend: n.leverage > 1.5 ? '偏高' : '正常', tone: n.leverage > 1.5 ? 'warn' : 'neutral' },
    { label: '净敞口', value: fmtPct(n.netExposure, false), trend: 'Beta 暴露', tone: 'neutral' },
    { label: '当日 VaR', value: fmtCurrency(n.varDaily, n.currency), trend: `95% · ${fmtPct(n.varPct, false)}`, tone: 'warn' },
  ]

  return (
    <div className="pf-nav-strip">
      {cells.map((c, i) => (
        <div className={`pf-nav-cell tone-${c.tone}`} key={i}>
          <span className="pf-nav-label">{c.label}</span>
          <strong className="pf-nav-value">{c.value}</strong>
          {c.trend && <span className="pf-nav-trend">{c.trend}</span>}
          <span className={`pf-nav-stripe stripe-${c.tone}`} />
        </div>
      ))}
    </div>
  )
}
