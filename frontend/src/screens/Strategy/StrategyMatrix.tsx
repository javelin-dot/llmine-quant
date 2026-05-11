import { useMemo, useState } from 'react'
import { useStrategy } from '../../contexts/StrategyContext'

type SortKey = 'annualReturn' | 'maxDd' | 'sharpe' | 'oosScore' | 'name'
type SortDir = 'asc' | 'desc'
type StatusFilter = 'all' | 'live' | 'paper' | 'backtest' | 'backtesting' | 'draft'

const STATUS_META: Record<string, { label: string; tone: string }> = {
  live: { label: 'Live', tone: 'green' },
  paper: { label: 'Paper', tone: 'yellow' },
  backtest: { label: 'Backtest', tone: 'blue' },
  backtesting: { label: '回测中', tone: 'purple' },
  draft: { label: 'Draft', tone: 'gray' },
}

const STATUS_FILTERS: { id: StatusFilter; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'live', label: 'Live' },
  { id: 'paper', label: 'Paper' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'backtesting', label: '回测中' },
  { id: 'draft', label: 'Draft' },
]

interface MicroSparkProps {
  data: number[]
  positive: boolean
}

function MicroSpark({ data, positive }: MicroSparkProps) {
  const w = 88
  const h = 26
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
  return (
    <svg className="matrix-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth={1.4} />
    </svg>
  )
}

interface StrategyMatrixProps {
  onNavigate?: (target: string) => void
  onOpenStrategy?: (id: string) => void
  highlightId?: string | null
}

export default function StrategyMatrix({ onOpenStrategy, highlightId }: StrategyMatrixProps) {
  const data = useStrategy()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [sortKey, setSortKey] = useState<SortKey>('annualReturn')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const rows = useMemo(() => {
    const filtered = data.matrix.filter((r) =>
      statusFilter === 'all' ? true : r.status === statusFilter
    )
    const sorted = [...filtered].sort((a, b) => {
      const cmp =
        sortKey === 'name'
          ? a.name.localeCompare(b.name)
          : (a[sortKey] as number) - (b[sortKey] as number)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [statusFilter, sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'name' ? 'asc' : 'desc')
    }
  }

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return '↕'
    return sortDir === 'asc' ? '↑' : '↓'
  }

  return (
    <div className="strategy-matrix">
      <div className="strategy-matrix-head">
        <div>
          <h4 className="strategy-matrix-title">Strategy Matrix</h4>
          <span className="strategy-matrix-sub">{rows.length} 个策略 · 按指标排序</span>
        </div>
        <div className="strategy-matrix-filters">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.id}
              className={`matrix-filter ${statusFilter === f.id ? 'active' : ''}`}
              onClick={() => setStatusFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <div className="strategy-matrix-table-wrap">
        <table className="strategy-matrix-table">
          <thead>
            <tr>
              <th className="th-sortable" onClick={() => toggleSort('name')}>
                策略 <span className="th-sort">{sortIcon('name')}</span>
              </th>
              <th>族群</th>
              <th className="th-sortable th-num" onClick={() => toggleSort('annualReturn')}>
                年化 <span className="th-sort">{sortIcon('annualReturn')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('maxDd')}>
                最大回撤 <span className="th-sort">{sortIcon('maxDd')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('sharpe')}>
                夏普 <span className="th-sort">{sortIcon('sharpe')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('oosScore')}>
                OOS <span className="th-sort">{sortIcon('oosScore')}</span>
              </th>
              <th>趋势</th>
              <th>状态</th>
              <th>更新</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const positive = r.annualReturn >= 0
              const meta = STATUS_META[r.status]
              return (
                <tr
                  key={r.id}
                  className={`matrix-row ${r.id === highlightId ? 'matrix-row-highlight' : ''}`}
                  onClick={() => onOpenStrategy?.(r.id)}
                >
                  <td className="td-name">
                    <strong>{r.name}</strong>
                  </td>
                  <td className="td-family">{r.family}</td>
                  <td className={`td-num ${positive ? 'pos' : 'neg'}`}>
                    {positive ? '+' : ''}
                    {(r.annualReturn * 100).toFixed(1)}%
                  </td>
                  <td className="td-num neg">
                    {(r.maxDd * 100).toFixed(1)}%
                  </td>
                  <td className="td-num">{r.sharpe.toFixed(2)}</td>
                  <td className="td-num">
                    <span
                      className={`oos-pill ${
                        r.oosScore >= 0.7 ? 'pos' : r.oosScore >= 0.5 ? 'mid' : 'neg'
                      }`}
                    >
                      {r.oosScore.toFixed(2)}
                    </span>
                  </td>
                  <td className="td-spark">
                    <MicroSpark data={r.sparkline} positive={positive} />
                  </td>
                  <td>
                    <span className={`matrix-status status-tag-${meta.tone}`}>
                      <span className={`status-dot-mini status-dot-${meta.tone}`} />
                      {meta.label}
                    </span>
                  </td>
                  <td className="td-time">{r.lastUpdate}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
