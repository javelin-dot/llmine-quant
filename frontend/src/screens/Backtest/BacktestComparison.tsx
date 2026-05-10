import { useMemo, useState } from 'react'
import { useBacktest } from '../../contexts/BacktestContext'

type SortKey = 'annualReturn' | 'maxDd' | 'sharpe' | 'oosScore' | 'name'
type SortDir = 'asc' | 'desc'

const STATUS_META: Record<string, { label: string; tone: string }> = {
  live: { label: 'Live', tone: 'green' },
  paper: { label: 'Paper', tone: 'yellow' },
  backtest: { label: 'Backtest', tone: 'blue' },
  draft: { label: 'Draft', tone: 'gray' },
}

const OVERFIT_META: Record<string, { label: string; tone: string }> = {
  low: { label: '低', tone: 'green' },
  medium: { label: '中', tone: 'yellow' },
  high: { label: '高', tone: 'red' },
}

interface SparkProps {
  data: number[]
  positive: boolean
}

function Spark({ data, positive }: SparkProps) {
  const w = 96
  const h = 28
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
    <svg className="bt-comparison-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth={1.4} />
    </svg>
  )
}

interface BacktestComparisonProps {
  onNavigate?: (target: string) => void
}

export default function BacktestComparison({ onNavigate }: BacktestComparisonProps) {
  const data = useBacktest()
  const [sortKey, setSortKey] = useState<SortKey>('oosScore')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const rows = useMemo(() => {
    const sorted = [...data.comparison].sort((a, b) => {
      const cmp =
        sortKey === 'name'
          ? a.name.localeCompare(b.name)
          : (a[sortKey] as number) - (b[sortKey] as number)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [sortKey, sortDir])

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
    <div className="bt-comparison">
      <div className="bt-comparison-head">
        <div>
          <h4 className="bt-comparison-title">Backtest Comparison</h4>
          <span className="bt-comparison-sub">AI 选出的 {rows.length} 个候选 · 按 {sortKey === 'oosScore' ? 'OOS' : sortKey} 排序</span>
        </div>
      </div>
      <div className="bt-comparison-table-wrap">
        <table className="bt-comparison-table">
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
              <th>过拟合</th>
              <th>趋势</th>
              <th>状态</th>
              <th>动作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const positive = r.annualReturn >= 0
              const status = STATUS_META[r.status]
              const overfit = OVERFIT_META[r.overfit]
              return (
                <tr
                  key={r.id}
                  className="bt-comparison-row"
                  onClick={() => onNavigate?.('explain')}
                >
                  <td className="td-name">
                    <strong>{r.name}</strong>
                  </td>
                  <td className="td-family">{r.family}</td>
                  <td className={`td-num ${positive ? 'pos' : 'neg'}`}>
                    {positive ? '+' : ''}
                    {(r.annualReturn * 100).toFixed(1)}%
                  </td>
                  <td className="td-num neg">{(r.maxDd * 100).toFixed(1)}%</td>
                  <td className="td-num">{r.sharpe.toFixed(2)}</td>
                  <td className="td-num">
                    <span
                      className={`bt-oos-pill ${
                        r.oosScore >= 0.7 ? 'pos' : r.oosScore >= 0.5 ? 'mid' : 'neg'
                      }`}
                    >
                      {r.oosScore.toFixed(2)}
                    </span>
                  </td>
                  <td>
                    <span className={`bt-overfit-tag tone-${overfit.tone}`}>{overfit.label}</span>
                  </td>
                  <td className="td-spark">
                    <Spark data={r.sparkline} positive={positive} />
                  </td>
                  <td>
                    <span className={`bt-status-tag status-tag-${status.tone}`}>
                      <span className={`status-dot-mini status-dot-${status.tone}`} />
                      {status.label}
                    </span>
                  </td>
                  <td>
                    <button
                      className="bt-comparison-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        onNavigate?.('explain')
                      }}
                    >
                      解释
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
