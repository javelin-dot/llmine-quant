import { mock } from '../../data'

function fmtSec(s: number): string {
  if (s < 60) return `${s}s`
  if (s < 3600) return `${(s / 60).toFixed(1)}m`
  return `${(s / 3600).toFixed(1)}h`
}

export default function ApprovalStrip() {
  const s = mock.execution.summary

  const cells: { label: string; value: string; trend?: string; tone: 'pos' | 'neg' | 'warn' | 'neutral' }[] = [
    { label: '待审批', value: `${s.pending}`, trend: '人工确认', tone: s.pending > 5 ? 'warn' : 'neutral' },
    { label: '紧急', value: `${s.urgent}`, trend: '< 3min 倒计时', tone: s.urgent > 0 ? 'neg' : 'neutral' },
    { label: '风险拦截', value: `${s.blocked}`, trend: 'Risk Agent 拒单', tone: 'warn' },
    { label: '24h 已批准', value: `${s.approved24h}`, trend: '今日累计', tone: 'pos' },
    { label: '平均时延', value: fmtSec(s.avgLatencySec), trend: '提交→成交', tone: 'neutral' },
    { label: '成功率', value: `${(s.successRate * 100).toFixed(1)}%`, trend: '过去 24h', tone: s.successRate >= 0.95 ? 'pos' : 'warn' },
  ]

  return (
    <div className="ex-approval-strip">
      {cells.map((c, i) => (
        <div className={`ex-strip-cell tone-${c.tone}`} key={i}>
          <span className="ex-strip-label">{c.label}</span>
          <strong className="ex-strip-value">{c.value}</strong>
          {c.trend && <span className="ex-strip-trend">{c.trend}</span>}
          <span className={`ex-strip-stripe stripe-${c.tone}`} />
        </div>
      ))}
    </div>
  )
}
