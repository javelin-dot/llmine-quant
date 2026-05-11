import { useMemo, useState } from 'react'
import { useStrategy } from '../../contexts/StrategyContext'

type SortKey = 'annualReturn' | 'maxDd' | 'sharpe' | 'oosScore' | 'name'
type SortDir = 'asc' | 'desc'

const STAGE_META: Record<string, { label: string; tone: string }> = {
  live: { label: '实盘', tone: 'green' },
  paper: { label: '模拟盘', tone: 'yellow' },
  backtest: { label: '回测', tone: 'blue' },
  backtesting: { label: '回测', tone: 'blue' },
  draft: { label: '草稿', tone: 'gray' },
  research: { label: '研究', tone: 'purple' },
  paused: { label: '暂停', tone: 'gray' },
}

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
  stageFilter?: string | null
}

export default function StrategyMatrix({ onOpenStrategy, highlightId, stageFilter }: StrategyMatrixProps) {
  const data = useStrategy()
  const [sortKey, setSortKey] = useState<SortKey>('annualReturn')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const rows = useMemo(() => {
    let filtered = data.matrix
    if (stageFilter) {
      // Map lifecycle filter keys to matrix status values
      const filterMap: Record<string, string[]> = {
        ideas: ['draft'],
        research: ['research'],
        backtest: ['backtest', 'backtesting'],
        paper: ['paper'],
        live: ['live'],
        paused: ['paused'],
      }
      const targetStatuses = filterMap[stageFilter] || [stageFilter]
      filtered = filtered.filter((r) => targetStatuses.includes(r.status))
    }
    const sorted = [...filtered].sort((a, b) => {
      const cmp =
        sortKey === 'name'
          ? a.name.localeCompare(b.name)
          : (a[sortKey] as number) - (b[sortKey] as number)
      return sortDir === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [data.matrix, stageFilter, sortKey, sortDir])

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

  const getActions = (status: string) => {
    switch (status) {
      case 'draft':
        return ['打开', '运行回测']
      case 'backtest':
      case 'backtesting':
        return ['打开', '推送模拟盘']
      case 'paper':
        return ['打开', '部署实盘', '暂停']
      case 'live':
        return ['打开', '暂停']
      case 'paused':
        return ['打开', '恢复']
      default:
        return ['打开']
    }
  }

  return (
    <div className="strategy-matrix">
      <div className="strategy-matrix-head">
        <div>
          <h4 className="strategy-matrix-title">策略矩阵</h4>
          <span className="strategy-matrix-sub">
            {rows.length} 个策略 · 策略组合、回测结果与部署状态
          </span>
        </div>
      </div>
      <div className="strategy-matrix-table-wrap">
        <table className="strategy-matrix-table">
          <thead>
            <tr>
              <th className="th-sortable" onClick={() => toggleSort('name')}>
                策略名称 <span className="th-sort">{sortIcon('name')}</span>
              </th>
              <th>类型</th>
              <th>股票池</th>
              <th className="th-sortable th-num" onClick={() => toggleSort('annualReturn')}>
                CAGR <span className="th-sort">{sortIcon('annualReturn')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('maxDd')}>
                最大回撤 <span className="th-sort">{sortIcon('maxDd')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('sharpe')}>
                Sharpe <span className="th-sort">{sortIcon('sharpe')}</span>
              </th>
              <th className="th-sortable th-num" onClick={() => toggleSort('oosScore')}>
                OOS 稳定性 <span className="th-sort">{sortIcon('oosScore')}</span>
              </th>
              <th>趋势</th>
              <th>阶段</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const positive = r.annualReturn >= 0
              const meta = STAGE_META[r.status] || { label: r.status, tone: 'gray' }
              const actions = getActions(r.status)
              return (
                <tr
                  key={r.id}
                  className={`matrix-row ${r.id === highlightId ? 'matrix-row-highlight' : ''}`}
                >
                  <td className="td-name" onClick={() => onOpenStrategy?.(r.id)}>
                    <strong>{r.name}</strong>
                  </td>
                  <td className="td-family" onClick={() => onOpenStrategy?.(r.id)}>
                    {r.family}
                  </td>
                  <td className="td-universe" onClick={() => onOpenStrategy?.(r.id)}>
                    —
                  </td>
                  <td className={`td-num ${positive ? 'pos' : 'neg'}`} onClick={() => onOpenStrategy?.(r.id)}>
                    {positive ? '+' : ''}
                    {(r.annualReturn * 100).toFixed(1)}%
                  </td>
                  <td className="td-num neg" onClick={() => onOpenStrategy?.(r.id)}>
                    {(r.maxDd * 100).toFixed(1)}%
                  </td>
                  <td className="td-num" onClick={() => onOpenStrategy?.(r.id)}>
                    {r.sharpe.toFixed(2)}
                  </td>
                  <td className="td-num" onClick={() => onOpenStrategy?.(r.id)}>
                    <span
                      className={`oos-pill ${
                        r.oosScore >= 0.7 ? 'pos' : r.oosScore >= 0.5 ? 'mid' : 'neg'
                      }`}
                    >
                      {r.oosScore.toFixed(2)}
                    </span>
                  </td>
                  <td className="td-spark" onClick={() => onOpenStrategy?.(r.id)}>
                    <MicroSpark data={r.sparkline} positive={positive} />
                  </td>
                  <td onClick={() => onOpenStrategy?.(r.id)}>
                    <span className={`matrix-status status-tag-${meta.tone}`}>
                      <span className={`status-dot-mini status-dot-${meta.tone}`} />
                      {meta.label}
                    </span>
                  </td>
                  <td className="td-time" onClick={() => onOpenStrategy?.(r.id)}>
                    {r.lastUpdate}
                  </td>
                  <td className="td-actions">
                    <div className="matrix-actions">
                      {actions.map((a) => (
                        <button
                          key={a}
                          className="matrix-action-btn"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (a === 'Open') onOpenStrategy?.(r.id)
                          }}
                        >
                          {a}
                        </button>
                      ))}
                    </div>
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
