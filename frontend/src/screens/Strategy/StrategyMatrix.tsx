import { useMemo, useRef, useState } from 'react'
import { useStrategy } from '../../contexts/StrategyContext'
import { api } from '../../lib/api'

type SortKey = 'annualReturn' | 'maxDd' | 'sharpe' | 'oosScore' | 'name'
type SortDir = 'asc' | 'desc'
type StageKey = 'all' | 'ideas' | 'research' | 'backtest' | 'paper' | 'live' | 'paused'
type DateRange = 'all' | '7d' | '30d' | '90d'

const STAGE_TABS: { key: StageKey; label: string; tone: string }[] = [
  { key: 'all', label: '全部', tone: 'gray' },
  { key: 'ideas', label: '草稿', tone: 'gray' },
  { key: 'research', label: '研究', tone: 'purple' },
  { key: 'backtest', label: '回测', tone: 'blue' },
  { key: 'paper', label: '模拟盘', tone: 'yellow' },
  { key: 'live', label: '实盘', tone: 'green' },
  { key: 'paused', label: '暂停', tone: 'gray' },
]

const STAGE_FILTER_MAP: Record<StageKey, string[]> = {
  all: [],
  ideas: ['draft'],
  research: ['research'],
  backtest: ['backtest', 'backtesting'],
  paper: ['paper'],
  live: ['live'],
  paused: ['paused'],
}

const STAGE_META: Record<string, { label: string; tone: string }> = {
  live: { label: '实盘', tone: 'green' },
  paper: { label: '模拟盘', tone: 'yellow' },
  backtest: { label: '回测', tone: 'blue' },
  backtesting: { label: '回测', tone: 'blue' },
  draft: { label: '草稿', tone: 'gray' },
  research: { label: '研究', tone: 'purple' },
  paused: { label: '暂停', tone: 'gray' },
}

const FAMILY_OPTIONS = ['all', 'trend', 'momentum', 'value', 'mean_reversion', 'arbitrage', 'multi-factor']
const FAMILY_LABELS: Record<string, string> = {
  all: '全部类型',
  trend: '趋势',
  momentum: '动量',
  value: '价值',
  mean_reversion: '均值回归',
  arbitrage: '套利',
  'multi-factor': '多因子',
}

const DATE_RANGE_OPTIONS: { key: DateRange; label: string }[] = [
  { key: 'all', label: '全部时间' },
  { key: '7d', label: '近7天' },
  { key: '30d', label: '近30天' },
  { key: '90d', label: '近90天' },
]

const PAGE_SIZE_OPTIONS = [10, 25, 50]

function MicroSpark({ data, positive }: { data: number[]; positive: boolean }) {
  const w = 80
  const h = 24
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
  return (
    <svg className="sm-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={positive ? '#4ff0a2' : '#ff5c7c'} strokeWidth={1.4} />
    </svg>
  )
}

interface StrategyMatrixProps {
  onNavigate?: (target: string) => void
  onOpenStrategy?: (id: string) => void
  highlightId?: string | null
  onRefresh?: () => void
}

export default function StrategyMatrix({ onNavigate, onOpenStrategy, highlightId, onRefresh }: StrategyMatrixProps) {
  const data = useStrategy()
  const [stageFilter, setStageFilter] = useState<StageKey>('all')
  const [familyFilter, setFamilyFilter] = useState('all')
  const [dateRange, setDateRange] = useState<DateRange>('all')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('annualReturn')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [pendingAction, setPendingAction] = useState<{ rowId: string; action: string } | null>(null)
  const [toast, setToast] = useState<{ tone: 'green' | 'red' | 'blue'; text: string } | null>(null)
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  const showToast = (tone: 'green' | 'red' | 'blue', text: string) => {
    setToast({ tone, text })
    setTimeout(() => setToast(null), 3000)
  }

  const handleAction = async (rowId: string, action: string) => {
    setOpenMenuId(null)
    if (pendingAction) return
    if (action === '打开') { onOpenStrategy?.(rowId); return }
    setPendingAction({ rowId, action })
    try {
      if (action === '开始研究') {
        await api.strategy.update(rowId, { status: 'research' })
        onRefresh?.()
        showToast('green', '已进入研究阶段，可运行回测')
      } else if (action === '运行回测') {
        // Draft strategies aren't visible to the backtest lab until they're in
        // research+ status, so auto-promote drafts before navigating.
        const row = data.matrix.find((m) => m.id === rowId)
        if (row && row.status === 'draft') {
          await api.strategy.update(rowId, { status: 'research' })
          onRefresh?.()
        }
        onNavigate?.(`backtest:strategyId=${encodeURIComponent(rowId)}`)
      } else if (action === '推送模拟盘') {
        const detail = await api.strategy.detail(rowId).catch(() => null)
        const market = detail?.market ?? 'A'
        const baseCurrency = market === 'crypto' ? 'USDT' : 'CNY'
        const name = detail?.name ?? rowId.slice(0, 8)
        const account = await api.paper.createAccount({
          name: `${name} · 模拟盘`,
          strategyId: rowId,
          market,
          baseCurrency,
          initialCash: 1_000_000,
        })
        await api.strategy.update(rowId, { status: 'paper' }).catch(() => null)
        onRefresh?.()
        showToast('green', `已创建模拟账户「${account.name}」`)
        setTimeout(() => onNavigate?.(`paper:accountId=${encodeURIComponent(account.id)}`), 800)
      } else if (action === '部署实盘') {
        await api.strategy.update(rowId, { status: 'live' })
        onRefresh?.()
        showToast('green', '已部署到实盘（需审批）')
        setTimeout(() => onNavigate?.('execution'), 1200)
      } else if (action === '暂停') {
        await api.strategy.update(rowId, { status: 'paused' })
        onRefresh?.()
        showToast('blue', '策略已暂停')
      } else if (action === '恢复') {
        await api.strategy.update(rowId, { status: 'live' })
        onRefresh?.()
        showToast('green', '策略已恢复')
      }
    } catch (err) {
      showToast('red', `${action}失败: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setPendingAction(null)
    }
  }

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = { all: data.matrix.length }
    STAGE_TABS.slice(1).forEach((t) => {
      const targets = STAGE_FILTER_MAP[t.key]
      counts[t.key] = data.matrix.filter((r) => targets.includes(r.status)).length
    })
    return counts
  }, [data.matrix])

  const filteredRows = useMemo(() => {
    let rows = data.matrix
    if (stageFilter !== 'all') {
      const targets = STAGE_FILTER_MAP[stageFilter]
      rows = rows.filter((r) => targets.includes(r.status))
    }
    if (familyFilter !== 'all') {
      rows = rows.filter((r) =>
        r.family.toLowerCase().replace(/[\s-]/g, '_') === familyFilter ||
        r.family.toLowerCase() === familyFilter
      )
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter((r) => r.name.toLowerCase().includes(q))
    }
    if (dateRange !== 'all') {
      const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90
      const cutoff = new Date()
      cutoff.setDate(cutoff.getDate() - days)
      rows = rows.filter((r) => {
        const d = new Date(r.lastUpdate)
        return !isNaN(d.getTime()) && d >= cutoff
      })
    }
    return [...rows].sort((a, b) => {
      const cmp =
        sortKey === 'name'
          ? a.name.localeCompare(b.name)
          : (a[sortKey] as number) - (b[sortKey] as number)
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data.matrix, stageFilter, familyFilter, dateRange, search, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const pageRows = filteredRows.slice((safePage - 1) * pageSize, safePage * pageSize)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir(key === 'name' ? 'asc' : 'desc') }
  }

  const sortIcon = (key: SortKey) => sortKey !== key ? '↕' : sortDir === 'asc' ? '↑' : '↓'

  const getPrimaryAction = (status: string) => {
    switch (status) {
      case 'draft': return '开始研究'
      case 'research': return '运行回测'
      case 'backtest': case 'backtesting': return '推送模拟盘'
      case 'paper': return '部署实盘'
      case 'live': return '暂停'
      case 'paused': return '恢复'
      default: return null
    }
  }

  const getMenuActions = (status: string) => {
    switch (status) {
      case 'draft': return ['运行回测']
      case 'research': return ['推送模拟盘']
      case 'backtest': case 'backtesting': return ['运行回测']
      case 'paper': return ['暂停']
      case 'live': return []
      case 'paused': return []
      default: return []
    }
  }

  const handleStageChange = (key: StageKey) => {
    setStageFilter(key)
    setPage(1)
  }

  const handleSearchChange = (v: string) => {
    setSearch(v)
    setPage(1)
  }

  const pageNums = useMemo(() => {
    const nums: (number | '…')[] = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) nums.push(i)
    } else {
      nums.push(1)
      if (safePage > 3) nums.push('…')
      for (let i = Math.max(2, safePage - 1); i <= Math.min(totalPages - 1, safePage + 1); i++) nums.push(i)
      if (safePage < totalPages - 2) nums.push('…')
      nums.push(totalPages)
    }
    return nums
  }, [totalPages, safePage])

  return (
    <div className="sf2-matrix">
      {/* Stage filter tabs */}
      <div className="sf2-stage-tabs">
        {STAGE_TABS.map((t) => (
          <button
            key={t.key}
            className={`sf2-stage-tab ${stageFilter === t.key ? 'active' : ''} tab-${t.tone}`}
            onClick={() => handleStageChange(t.key)}
          >
            {t.label}
            <span className="sf2-tab-count">{stageCounts[t.key] ?? 0}</span>
          </button>
        ))}
      </div>

      {/* Filter bar */}
      <div className="sf2-filter-bar">
        <div className="sf2-filter-left">
          <select
            className="sf2-select"
            value={familyFilter}
            onChange={(e) => { setFamilyFilter(e.target.value); setPage(1) }}
          >
            {FAMILY_OPTIONS.map((o) => (
              <option key={o} value={o}>{FAMILY_LABELS[o]}</option>
            ))}
          </select>
          <select
            className="sf2-select"
            value={dateRange}
            onChange={(e) => { setDateRange(e.target.value as DateRange); setPage(1) }}
          >
            {DATE_RANGE_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>{o.label}</option>
            ))}
          </select>
          <div className="sf2-search-wrap">
            <span className="sf2-search-icon">⌕</span>
            <input
              className="sf2-search"
              type="text"
              placeholder="搜索策略名称…"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
            />
            {search && (
              <button className="sf2-search-clear" onClick={() => handleSearchChange('')}>✕</button>
            )}
          </div>
        </div>
        <div className="sf2-filter-right">
          {toast && (
            <div className={`sf2-toast sf2-toast-${toast.tone}`}>{toast.text}</div>
          )}
          <span className="sf2-result-count">
            共 <strong>{filteredRows.length}</strong> 条
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="sf2-table-wrap" onClick={() => setOpenMenuId(null)}>
        <table className="sf2-table">
          <thead>
            <tr>
              <th className="th-sortable" onClick={() => toggleSort('name')}>
                策略名称 <span className="th-sort">{sortIcon('name')}</span>
              </th>
              <th>类型</th>
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
                OOS <span className="th-sort">{sortIcon('oosScore')}</span>
              </th>
              <th>趋势</th>
              <th>阶段</th>
              <th>更新时间</th>
              <th className="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={10} className="sf2-empty-row">
                  暂无符合条件的策略
                </td>
              </tr>
            ) : (
              pageRows.map((r) => {
                const positive = r.annualReturn >= 0
                const meta = STAGE_META[r.status] || { label: r.status, tone: 'gray' }
                const primary = getPrimaryAction(r.status)
                const menuItems = getMenuActions(r.status)
                const isPrimaryPending = pendingAction?.rowId === r.id && pendingAction.action === primary
                return (
                  <tr
                    key={r.id}
                    className={`sf2-row ${r.id === highlightId ? 'sf2-row-highlight' : ''}`}
                    onClick={() => { setOpenMenuId(null); onOpenStrategy?.(r.id) }}
                  >
                    <td className="td-name">
                      <span className="sf2-name-text">{r.name}</span>
                    </td>
                    <td>
                      <span className="sf2-family-badge">{r.family}</span>
                    </td>
                    <td className={`td-num ${positive ? 'pos' : 'neg'}`}>
                      {positive ? '+' : ''}{(r.annualReturn * 100).toFixed(1)}%
                    </td>
                    <td className="td-num neg">
                      {(r.maxDd * 100).toFixed(1)}%
                    </td>
                    <td className="td-num">
                      {r.sharpe.toFixed(2)}
                    </td>
                    <td className="td-num">
                      <span className={`sf2-oos-pill ${r.oosScore >= 0.7 ? 'pos' : r.oosScore >= 0.5 ? 'mid' : 'neg'}`}>
                        {r.oosScore.toFixed(2)}
                      </span>
                    </td>
                    <td className="td-spark">
                      <MicroSpark data={r.sparkline} positive={positive} />
                    </td>
                    <td>
                      <span className={`sf2-stage-tag status-tag-${meta.tone}`}>
                        <span className={`status-dot-mini status-dot-${meta.tone}`} />
                        {meta.label}
                      </span>
                    </td>
                    <td className="td-time">{r.lastUpdate}</td>
                    <td className="td-actions" onClick={(e) => e.stopPropagation()}>
                      <div className="sf2-row-actions">
                        <button
                          className="sf2-btn-open"
                          onClick={() => onOpenStrategy?.(r.id)}
                        >
                          打开
                        </button>
                        {primary && (
                          <button
                            className="sf2-btn-primary"
                            disabled={!!isPrimaryPending}
                            onClick={() => void handleAction(r.id, primary)}
                          >
                            {isPrimaryPending ? '…' : primary}
                          </button>
                        )}
                        {menuItems.length > 0 && (
                          <div className="sf2-menu-wrap" ref={openMenuId === r.id ? menuRef : null}>
                            <button
                              className="sf2-btn-menu"
                              onClick={(e) => { e.stopPropagation(); setOpenMenuId(openMenuId === r.id ? null : r.id) }}
                            >
                              ⋯
                            </button>
                            {openMenuId === r.id && (
                              <div className="sf2-dropdown">
                                {menuItems.map((a) => (
                                  <button
                                    key={a}
                                    className="sf2-dropdown-item"
                                    onClick={() => void handleAction(r.id, a)}
                                  >
                                    {a}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="sf2-pagination">
        <div className="sf2-page-left">
          <span className="sf2-page-info">
            显示 {filteredRows.length === 0 ? 0 : (safePage - 1) * pageSize + 1}–{Math.min(safePage * pageSize, filteredRows.length)} / {filteredRows.length} 条
          </span>
          <span className="sf2-page-size-label">每页</span>
          <select
            className="sf2-select sf2-page-size-select"
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
          >
            {PAGE_SIZE_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div className="sf2-page-right">
          <button
            className="sf2-page-btn"
            disabled={safePage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            ‹
          </button>
          {pageNums.map((n, i) =>
            n === '…' ? (
              <span key={`ellipsis-${i}`} className="sf2-page-ellipsis">…</span>
            ) : (
              <button
                key={n}
                className={`sf2-page-btn sf2-page-num ${safePage === n ? 'active' : ''}`}
                onClick={() => setPage(n as number)}
              >
                {n}
              </button>
            )
          )}
          <button
            className="sf2-page-btn"
            disabled={safePage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            ›
          </button>
        </div>
      </div>
    </div>
  )
}
