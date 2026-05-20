import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  type PaperAccount,
  type PaperAccountCreatePayload,
  type PaperNavPoint,
  type PaperOrder,
  type PaperPosition,
  type PaperEvaluationSnapshot,
  type PaperRiskBreach,
  type ManualPaperOrderPayload,
  type RunEodSummary,
  type StrategyDetail,
  type StrategyListItem,
} from '../../lib/api'
import * as echarts from 'echarts'

interface PaperProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
  initialAccountId?: string
}

function fmtPct(v: number | null | undefined, d = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(d)}%`
}

function fmtCny(v: number | null | undefined): string {
  if (v == null) return '—'
  return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtQty(v: number | null | undefined): string {
  if (v == null) return '—'
  return v.toLocaleString('zh-CN', { maximumFractionDigits: Math.abs(v % 1) < 1e-9 ? 0 : 4 })
}

function toneClass(v: number | null | undefined): string {
  if (v == null) return ''
  return v >= 0 ? 'pos' : 'neg'
}

function sessionLabel(status: string | undefined) {
  switch (status) {
    case 'call_auction': return '集合竞价'
    case 'continuous': return '连续竞价'
    case 'closing_auction': return '收盘竞价'
    case 'lunch_break': return '午间休市'
    default: return '已收盘'
  }
}

function actionLabel(action: string) {
  switch (action) {
    case 'open': return '建仓'
    case 'increase': return '加仓'
    case 'decrease': return '减仓'
    case 'close': return '平仓'
    default: return '持有'
  }
}

// ── NAV Mini Chart ───────────────────────────────────────────────────────────

function NavChart({ data }: { data: PaperNavPoint[] }) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!ref.current) return
    chartRef.current = echarts.init(ref.current, 'dark', { renderer: 'canvas' })
    return () => { chartRef.current?.dispose(); chartRef.current = null }
  }, [])

  useEffect(() => {
    if (!chartRef.current || !data.length) return
    const dates = data.map((d) => d.tradeDate)
    const navs = data.map((d) => d.nav)
    const dds = data.map((d) => d.drawdown ?? 0)
    chartRef.current.setOption({
      backgroundColor: 'transparent',
      grid: [
        { top: 16, left: 48, right: 16, bottom: 80 },
        { top: '72%', left: 48, right: 16, bottom: 32 },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#333' } } },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { fontSize: 9, color: '#666' }, axisLine: { lineStyle: { color: '#333' } } },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, axisLabel: { fontSize: 10, color: '#888', formatter: (v: number) => v.toFixed(2) }, splitLine: { lineStyle: { color: '#1a1a2e' } } },
        { type: 'value', gridIndex: 1, axisLabel: { fontSize: 9, color: '#888', formatter: (v: number) => `${(v * 100).toFixed(1)}%` }, splitLine: { lineStyle: { color: '#1a1a2e' } } },
      ],
      series: [
        {
          name: 'NAV', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: navs,
          smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#6df3b6' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(109,243,182,0.25)' }, { offset: 1, color: 'rgba(109,243,182,0)' }]) },
        },
        {
          name: '回撤', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: dds,
          itemStyle: { color: '#ff7d96', opacity: 0.7 },
        },
      ],
      tooltip: { trigger: 'axis', backgroundColor: '#0d1117', borderColor: '#30363d', textStyle: { color: '#e6edf3', fontSize: 11 } },
    })
  }, [data])

  return <div ref={ref} className="paper-nav-chart" />
}

// ── Account Switcher ─────────────────────────────────────────────────────────

function AccountSwitcher({
  accounts,
  selectedId,
  onSelect,
}: {
  accounts: PaperAccount[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = accounts.find((a) => a.id === selectedId)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  if (!accounts.length) {
    return <div className="paper-account-switcher empty">暂无账户</div>
  }

  const pnlPct = selected && selected.initialCash > 0
    ? (selected.cash - selected.initialCash) / selected.initialCash
    : null

  return (
    <div className={`paper-account-switcher ${open ? 'open' : ''}`} ref={rootRef}>
      <button
        type="button"
        className="paper-account-switcher-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="paper-account-switcher-label">当前账户</span>
        <span className="paper-account-switcher-name">{selected?.name ?? '选择账户'}</span>
        {selected && (
          <span className={`paper-account-switcher-pnl ${toneClass(pnlPct)}`}>{fmtPct(pnlPct)}</span>
        )}
        <span className="paper-account-switcher-caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="paper-account-switcher-menu" role="listbox">
          {accounts.map((account) => {
            const ret = account.initialCash > 0
              ? (account.cash - account.initialCash) / account.initialCash
              : null
            return (
              <button
                key={account.id}
                type="button"
                role="option"
                aria-selected={account.id === selectedId}
                className={`paper-account-switcher-item ${account.id === selectedId ? 'on' : ''}`}
                onClick={() => { onSelect(account.id); setOpen(false) }}
              >
                <div className="paper-account-switcher-item-head">
                  <strong>{account.name}</strong>
                  <span className={`paper-account-switcher-pnl ${toneClass(ret)}`}>{fmtPct(ret)}</span>
                </div>
                <div className="paper-account-switcher-item-meta">
                  <span className="status-tag-blue">{account.market}</span>
                  <span className={`status-tag-${account.status === 'active' ? 'green' : account.status === 'paused' ? 'yellow' : 'gray'}`}>{account.status}</span>
                  <span>{fmtCny(account.cash)}</span>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Create Account Modal ─────────────────────────────────────────────────────

function CreateAccountModal({ onClose, onCreated }: { onClose: () => void; onCreated: (a: PaperAccount) => void }) {
  const [form, setForm] = useState<PaperAccountCreatePayload>({
    name: '',
    market: 'ashare',
    baseCurrency: 'CNY',
    initialCash: 1_000_000,
    inceptionDate: new Date().toISOString().slice(0, 10),
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    if (!form.name.trim()) { setError('请填写账户名称'); return }
    setLoading(true); setError(null)
    try {
      const acc = await api.paper.createAccount(form)
      onCreated(acc)
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop show paper-create-modal-backdrop" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="paper-create-modal" onClick={(e) => e.stopPropagation()}>
        <div className="paper-create-modal-head">
          <div>
            <h3>新建模拟账户</h3>
            <p>创建独立模拟盘，绑定策略后可运行 EOD 跟踪</p>
          </div>
          <button type="button" className="paper-create-modal-close" onClick={onClose} aria-label="关闭">×</button>
        </div>
        <div className="paper-create-form">
          <div className="paper-form-row">
            <label className="paper-form-label">名称</label>
            <input className="bt-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：MA趋势模拟盘" />
          </div>
          <div className="paper-form-grid">
            <div className="paper-form-row">
              <label className="paper-form-label">市场</label>
              <select className="bt-input" value={form.market} onChange={(e) => setForm({ ...form, market: e.target.value })}>
                <option value="ashare">A股</option>
                <option value="crypto">加密</option>
              </select>
            </div>
            <div className="paper-form-row">
              <label className="paper-form-label">初始资金</label>
              <input type="number" className="bt-input" value={form.initialCash} min={10000} step={100000}
                onChange={(e) => setForm({ ...form, initialCash: Number(e.target.value) })} />
            </div>
          </div>
          <div className="paper-form-row">
            <label className="paper-form-label">开始日期</label>
            <input type="date" className="bt-input" value={form.inceptionDate ?? ''}
              onChange={(e) => setForm({ ...form, inceptionDate: e.target.value })} />
          </div>
          {error && <div className="bt-toast bt-toast-red">{error}</div>}
        </div>
        <div className="paper-create-modal-actions">
          <button type="button" className="bt-btn" onClick={onClose}>取消</button>
          <button type="button" className="bt-btn bt-btn-primary" disabled={loading} onClick={() => void submit()}>
            {loading ? '创建中…' : '创建账户'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Account Detail ───────────────────────────────────────────────────────────

interface DetailState {
  nav: PaperNavPoint[]
  positions: PaperPosition[]
  orders: PaperOrder[]
  breaches: PaperRiskBreach[]
  evaluation: PaperEvaluationSnapshot | null
}
const EMPTY_DETAIL: DetailState = { nav: [], positions: [], orders: [], breaches: [], evaluation: null }

function AccountDetail({ account, onAccountUpdated }: { account: PaperAccount; onAccountUpdated: (account: PaperAccount) => void }) {
  const accountId = account.id
  const [detail, setDetail] = useState<DetailState>(EMPTY_DETAIL)
  const [view, setView] = useState<'overview' | 'trading' | 'performance'>('trading')
  const [tab, setTab] = useState<'positions' | 'orders' | 'breaches'>('positions')
  const [eodDate, setEodDate] = useState(new Date().toISOString().slice(0, 10))
  const [eodLoading, setEodLoading] = useState(false)
  const [eodResult, setEodResult] = useState<RunEodSummary | null>(null)
  const [eodError, setEodError] = useState<string | null>(null)
  const [tradeForm, setTradeForm] = useState<ManualPaperOrderPayload>({
    symbol: '',
    side: 'buy',
    quantity: 100,
    reason: 'manual_order',
    executionMode: 'immediate',
  })
  const [tradeLoading, setTradeLoading] = useState(false)
  const [tradeMessage, setTradeMessage] = useState<string | null>(null)
  const [editingOrderId, setEditingOrderId] = useState<string | null>(null)
  const [orderFilter, setOrderFilter] = useState<'all' | 'open' | 'done'>('all')
  const [matchLoading, setMatchLoading] = useState(false)
  const [strategies, setStrategies] = useState<StrategyListItem[]>([])
  const [selectedStrategyId, setSelectedStrategyId] = useState(account.strategyId ?? '')
  const [selectedStrategyDetail, setSelectedStrategyDetail] = useState<StrategyDetail | null>(null)
  const [selectedVersionId, setSelectedVersionId] = useState(account.strategyVersionId ?? '')
  const [bindLoading, setBindLoading] = useState(false)
  const [bindMessage, setBindMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    const [nav, positions, orders, breaches, evaluation] = await Promise.all([
      api.paper.nav(accountId).catch(() => []),
      api.paper.positions(accountId).catch(() => []),
      api.paper.orders(accountId).catch(() => []),
      api.paper.breaches(accountId).catch(() => []),
      api.paper.evaluation(accountId).catch(() => null),
    ])
    setDetail({
      nav: nav as PaperNavPoint[],
      positions: positions as PaperPosition[],
      orders: orders as PaperOrder[],
      breaches: breaches as PaperRiskBreach[],
      evaluation: evaluation as PaperEvaluationSnapshot | null,
    })
  }, [accountId])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load() }, [load])
  useEffect(() => {
    void api.strategy.list().then((res) => setStrategies(res.items)).catch(() => setStrategies([]))
  }, [])
  useEffect(() => {
    setSelectedStrategyId(account.strategyId ?? '')
    setSelectedVersionId(account.strategyVersionId ?? '')
  }, [account.strategyId, account.strategyVersionId])
  useEffect(() => {
    if (!selectedStrategyId) {
      setSelectedStrategyDetail(null)
      return
    }
    void api.strategy.detail(selectedStrategyId)
      .then((detail) => {
        setSelectedStrategyDetail(detail)
        setSelectedVersionId((current) =>
          detail.versions.some((version) => version.id === current)
            ? current
            : detail.versions[0]?.id ?? '',
        )
      })
      .catch(() => setSelectedStrategyDetail(null))
  }, [selectedStrategyId])
  const { nav, positions, orders, breaches, evaluation } = detail

  const runEod = async () => {
    setEodLoading(true); setEodError(null); setEodResult(null)
    try {
      const r = await api.paper.runEod(accountId, eodDate)
      setEodResult(r)
      await load()
    } catch (e) {
      setEodError(e instanceof Error ? e.message : 'EOD 失败')
    } finally {
      setEodLoading(false)
    }
  }

  const latestNav = nav[nav.length - 1]
  const grossExposure = latestNav && latestNav.nav > 0 ? latestNav.marketValue / latestNav.nav : 0
  const quickSubmit = (symbol: string, side: 'buy' | 'sell', quantity: number) => {
    setEditingOrderId(null)
    setTradeForm({ symbol, side, quantity, reason: side === 'buy' ? 'manual_add' : 'manual_reduce', executionMode: 'immediate' })
  }
  const submitTrade = async () => {
    if (!tradeForm.symbol.trim()) return
    setTradeLoading(true); setTradeMessage(null)
    try {
      const order = editingOrderId
        ? await api.paper.replaceOrder(accountId, editingOrderId, tradeForm.quantity)
        : await api.paper.submitOrder(accountId, tradeForm)
      setTradeMessage(editingOrderId
        ? `${order.symbol} 委托已改为 ${order.targetQuantity}`
        : `${order.symbol} ${order.side.toUpperCase()} ${order.status}`)
      setEditingOrderId(null)
      await load()
    } catch (e) {
      setTradeMessage(e instanceof Error ? e.message : '提交失败')
    } finally {
      setTradeLoading(false)
    }
  }
  const startReplace = (order: PaperOrder) => {
    setEditingOrderId(order.id)
    setTradeForm({
      symbol: order.symbol,
      side: order.side as 'buy' | 'sell',
      quantity: order.targetQuantity,
      reason: order.reason ?? 'manual_replace',
      executionMode: 'queue',
    })
  }
  const cancelOrder = async (order: PaperOrder) => {
    setTradeMessage(null)
    try {
      await api.paper.cancelOrder(accountId, order.id)
      setTradeMessage(`${order.symbol} 委托已撤销`)
      await load()
    } catch (e) {
      setTradeMessage(e instanceof Error ? e.message : '撤单失败')
    }
  }
  const matchOrders = async () => {
    setMatchLoading(true); setTradeMessage(null)
    try {
      const result = await api.paper.matchOrders(accountId)
      setTradeMessage(`撮合完成 · 成交 ${result.ordersFilled} · 拒绝 ${result.ordersRejected}`)
      await load()
    } catch (e) {
      setTradeMessage(e instanceof Error ? e.message : '撮合失败')
    } finally {
      setMatchLoading(false)
    }
  }
  const bindStrategy = async () => {
    if (!selectedStrategyId || !selectedVersionId) return
    setBindLoading(true); setBindMessage(null)
    try {
      const updated = await api.paper.bindStrategy(accountId, {
        strategyId: selectedStrategyId,
        strategyVersionId: selectedVersionId,
      })
      onAccountUpdated(updated)
      setBindMessage('策略版本已绑定')
      await load()
    } catch (e) {
      setBindMessage(e instanceof Error ? e.message : '绑定失败')
    } finally {
      setBindLoading(false)
    }
  }
  const visibleOrders = orders.filter((order) => {
    if (orderFilter === 'open') return ['pending', 'approved'].includes(order.status)
    if (orderFilter === 'done') return !['pending', 'approved'].includes(order.status)
    return true
  })
  const openOrderCount = orders.filter((o) => ['pending', 'approved'].includes(o.status)).length

  const strategyLabel = selectedStrategyDetail?.name ?? '未绑定策略'
  const versionLabel = selectedStrategyDetail && selectedVersionId
    ? selectedStrategyDetail.versions.find((version) => version.id === selectedVersionId)?.version
    : null

  return (
    <div className="paper-console">
      <div className="paper-status-strip">
        <div className="paper-status-main">
          <div className="paper-status-title">
            <h3>{account.name}</h3>
            <span className="paper-status-strategy">{strategyLabel}{versionLabel ? ` · ${versionLabel}` : ''}</span>
          </div>
          <div className="paper-status-tags">
            <span className={`status-tag-${account.strategyVersionId ? 'green' : 'gray'}`}>{account.strategyVersionId ? 'tracking' : 'unbound'}</span>
            <span className={`status-tag-${account.status === 'active' ? 'green' : 'yellow'}`}>{account.status}</span>
          </div>
        </div>
        <div className="paper-status-metrics">
          <div className="paper-metric">
            <span>NAV</span>
            <strong className="tone-green">{latestNav ? fmtCny(latestNav.nav) : fmtCny(account.initialCash)}</strong>
          </div>
          <div className="paper-metric">
            <span>现金</span>
            <strong>{latestNav ? fmtCny(latestNav.cash) : fmtCny(account.cash)}</strong>
          </div>
          <div className="paper-metric">
            <span>仓位</span>
            <strong>{fmtPct(evaluation?.currentGross ?? grossExposure)}</strong>
          </div>
          <div className="paper-metric">
            <span>目标</span>
            <strong>{fmtPct(evaluation?.targetGross)}</strong>
          </div>
          <div className="paper-metric">
            <span>偏差</span>
            <strong className={toneClass(evaluation?.driftGross)}>{fmtPct(evaluation?.driftGross)}</strong>
          </div>
          <div className="paper-metric">
            <span>阶段</span>
            <strong>{sessionLabel(evaluation?.sessionStatus)}</strong>
          </div>
        </div>
        <div className="paper-status-actions">
          <input type="date" className="bt-input small" value={eodDate}
            onChange={(e) => setEodDate(e.target.value)} />
          <button type="button" className="bt-btn" disabled={eodLoading} onClick={() => void runEod()}>
            {eodLoading ? 'EOD…' : '运行 EOD'}
          </button>
        </div>
      </div>

      {(eodResult || eodError) && (
        <div className="paper-toast-row">
          {eodResult && (
            <div className="bt-toast bt-toast-green">
              EOD {eodResult.tradeDate} · 下单 {eodResult.ordersCreated} · 成交 {eodResult.ordersFilled} · NAV {fmtCny(eodResult.nav)}
            </div>
          )}
          {eodError && <div className="bt-toast bt-toast-red">{eodError}</div>}
        </div>
      )}

      <div className="paper-section-tabs">
        <button type="button" className={view === 'trading' ? 'active' : ''} onClick={() => setView('trading')}>交易执行</button>
        <button type="button" className={view === 'overview' ? 'active' : ''} onClick={() => setView('overview')}>账户概览</button>
        <button type="button" className={view === 'performance' ? 'active' : ''} onClick={() => setView('performance')}>绩效分析</button>
      </div>

      <div className="paper-view-shell">
        {view === 'trading' && (
          <div className="paper-trading-desk">
            <section className="paper-blotter">
              <div className="paper-blotter-head">
                <div className="bt-tabs bt-tabs-sticky">
                  <button type="button" className={`bt-tab ${tab === 'positions' ? 'on' : ''}`} onClick={() => setTab('positions')}>
                    持仓 <em>{positions.length}</em>
                  </button>
                  <button type="button" className={`bt-tab ${tab === 'orders' ? 'on' : ''}`} onClick={() => setTab('orders')}>
                    委托 <em>{openOrderCount || orders.length}</em>
                  </button>
                  <button type="button" className={`bt-tab ${tab === 'breaches' ? 'on' : ''}`} onClick={() => setTab('breaches')}>
                    风控 {breaches.length > 0 && <span className="paper-breach-badge">{breaches.length}</span>}
                  </button>
                </div>
                {tab === 'orders' && (
                  <div className="paper-order-toolbar">
                    <div className="paper-order-filters">
                      <button type="button" className={orderFilter === 'all' ? 'active' : ''} onClick={() => setOrderFilter('all')}>全部</button>
                      <button type="button" className={orderFilter === 'open' ? 'active' : ''} onClick={() => setOrderFilter('open')}>活动</button>
                      <button type="button" className={orderFilter === 'done' ? 'active' : ''} onClick={() => setOrderFilter('done')}>已结束</button>
                    </div>
                    <button type="button" className="bt-btn bt-btn-sm" disabled={matchLoading || openOrderCount === 0} onClick={() => void matchOrders()}>
                      {matchLoading ? '撮合中…' : '撮合活动委托'}
                    </button>
                  </div>
                )}
              </div>

              <div className="paper-blotter-body">
                {tab === 'positions' && (
                  positions.length === 0 ? (
                    <div className="paper-blotter-empty">暂无持仓 · 运行 EOD 或手动下单后显示</div>
                  ) : (
                    <div className="paper-blotter-scroll">
                      <table className="bt-table paper-desk-table">
                        <thead>
                          <tr><th>标的</th><th>总持仓</th><th>可卖</th><th>今日买入</th><th>均价</th><th>最新价</th><th>市值</th><th>权重</th><th>操作</th></tr>
                        </thead>
                        <tbody>
                          {positions.map((p) => (
                            <tr key={p.symbol}>
                              <td className="paper-symbol">{p.symbol}</td>
                              <td>{fmtQty(p.quantity)}</td>
                              <td>{fmtQty(p.availableQuantity)}</td>
                              <td>{fmtQty(p.todayBuyQuantity)}</td>
                              <td>{fmtCny(p.avgCost)}</td>
                              <td>{p.lastPrice != null ? fmtCny(p.lastPrice) : '—'}</td>
                              <td>{fmtCny(p.marketValue)}</td>
                              <td>{fmtPct(p.weight)}</td>
                              <td>
                                <div className="paper-row-actions">
                                  <button type="button" onClick={() => quickSubmit(p.symbol, 'buy', 100)}>加仓</button>
                                  <button type="button" disabled={p.availableQuantity <= 0} onClick={() => quickSubmit(p.symbol, 'sell', Math.min(100, p.availableQuantity))}>减仓</button>
                                  <button type="button" disabled={p.availableQuantity <= 0} onClick={() => quickSubmit(p.symbol, 'sell', p.availableQuantity)}>平仓</button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
                {tab === 'orders' && (
                  orders.length === 0 ? (
                    <div className="paper-blotter-empty">暂无委托</div>
                  ) : (
                    <div className="paper-blotter-scroll">
                      <table className="bt-table paper-desk-table">
                        <thead>
                          <tr><th>日期</th><th>标的</th><th>方向</th><th>委托</th><th>成交</th><th>剩余</th><th>状态</th><th>原因</th><th>操作</th></tr>
                        </thead>
                        <tbody>
                          {visibleOrders.map((o) => (
                            <tr key={o.id}>
                              <td className="bt-date">{o.tradeDate}</td>
                              <td className="paper-symbol">{o.symbol}</td>
                              <td className={o.side === 'buy' ? 'pos' : 'neg'}>{o.side.toUpperCase()}</td>
                              <td>{fmtQty(o.targetQuantity)}</td>
                              <td>{fmtQty(o.filledQuantity)}</td>
                              <td>{fmtQty(Math.max(0, o.targetQuantity - o.filledQuantity))}</td>
                              <td>
                                <span className={`status-tag-${o.status === 'filled' ? 'green' : ['rejected', 'canceled'].includes(o.status) ? 'red' : 'yellow'}`}>
                                  {o.status}
                                </span>
                              </td>
                              <td className="bt-trade-reason">{o.rejectionReason ?? o.reason ?? '—'}</td>
                              <td>
                                {['pending', 'approved'].includes(o.status) ? (
                                  <div className="paper-row-actions">
                                    <button type="button" onClick={() => startReplace(o)}>改单</button>
                                    <button type="button" onClick={() => void cancelOrder(o)}>撤单</button>
                                  </div>
                                ) : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
                {tab === 'breaches' && (
                  breaches.length === 0 ? (
                    <div className="paper-blotter-empty">无风控触发</div>
                  ) : (
                    <div className="paper-blotter-scroll">
                      <table className="bt-table paper-desk-table">
                        <thead>
                          <tr><th>日期</th><th>规则</th><th>严重度</th><th>详情</th><th>状态</th></tr>
                        </thead>
                        <tbody>
                          {breaches.map((b) => (
                            <tr key={b.id}>
                              <td className="bt-date">{b.tradeDate}</td>
                              <td>{b.rule}</td>
                              <td>
                                <span className={`status-tag-${b.severity === 'critical' ? 'red' : b.severity === 'high' ? 'red' : b.severity === 'medium' ? 'yellow' : 'green'}`}>
                                  {b.severity}
                                </span>
                              </td>
                              <td className="bt-trade-reason">{b.detail ?? '—'}</td>
                              <td>{b.status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>
            </section>

            <aside className="paper-order-ticket">
              <div className="paper-order-ticket-head">
                <h3>下单</h3>
                <span>A股 T+1 · 100 股整数手</span>
              </div>
              {editingOrderId && (
                <div className="paper-replace-banner">
                  正在改单
                  <button type="button" onClick={() => setEditingOrderId(null)}>退出</button>
                </div>
              )}
              <label>标的</label>
              <input className="bt-input" disabled={!!editingOrderId} placeholder="600519.SH" value={tradeForm.symbol} onChange={(e) => setTradeForm((v) => ({ ...v, symbol: e.target.value }))} />
              <label>方向</label>
              <div className="paper-side-toggle">
                <button type="button" disabled={!!editingOrderId} className={tradeForm.side === 'buy' ? 'active' : ''} onClick={() => setTradeForm((v) => ({ ...v, side: 'buy' }))}>买入</button>
                <button type="button" disabled={!!editingOrderId} className={tradeForm.side === 'sell' ? 'active' : ''} onClick={() => setTradeForm((v) => ({ ...v, side: 'sell' }))}>卖出</button>
              </div>
              {!editingOrderId && (
                <>
                  <label>执行</label>
                  <div className="paper-side-toggle">
                    <button type="button" className={tradeForm.executionMode === 'immediate' ? 'active' : ''} onClick={() => setTradeForm((v) => ({ ...v, executionMode: 'immediate' }))}>即时撮合</button>
                    <button type="button" className={tradeForm.executionMode === 'queue' ? 'active' : ''} onClick={() => setTradeForm((v) => ({ ...v, executionMode: 'queue' }))}>挂单</button>
                  </div>
                </>
              )}
              <label>数量</label>
              <input type="number" min={1} step={tradeForm.side === 'buy' ? 100 : 1} className="bt-input" value={tradeForm.quantity} onChange={(e) => setTradeForm((v) => ({ ...v, quantity: Number(e.target.value) }))} />
              <button type="button" className="bt-btn bt-btn-primary paper-order-submit" disabled={tradeLoading} onClick={() => void submitTrade()}>
                {tradeLoading ? '提交中…' : editingOrderId ? '确认改单' : tradeForm.executionMode === 'queue' ? '提交委托' : '提交并撮合'}
              </button>
              {tradeMessage && <div className="paper-trade-message">{tradeMessage}</div>}
            </aside>
          </div>
        )}

        {view === 'overview' && (
          <div className="paper-overview-view">
            <section className="paper-target-panel">
              <div className="paper-panel-head compact">
                <div>
                  <h3>目标仓位与偏差</h3>
                  <p>
                    {!evaluation?.strategyBound
                      ? '绑定策略版本后生成目标仓位与偏差评估'
                      : evaluation?.tradeDate
                        ? `基于 ${evaluation.tradeDate} 行情快照`
                        : '暂无可用行情快照'}
                  </p>
                </div>
              </div>
              {!evaluation || evaluation.targets.length === 0 ? (
                <div className="paper-blotter-empty">暂无目标仓位</div>
              ) : (
                <div className="paper-blotter-scroll paper-overview-scroll">
                  <table className="bt-table paper-desk-table">
                    <thead><tr><th>标的</th><th>当前权重</th><th>目标权重</th><th>偏差</th><th>当前数量</th><th>目标数量</th><th>建议动作</th><th>依据</th></tr></thead>
                    <tbody>{evaluation.targets.map((row) => <tr key={row.symbol}>
                      <td className="paper-symbol">{row.symbol}</td>
                      <td>{fmtPct(row.currentWeight)}</td>
                      <td>{fmtPct(row.targetWeight)}</td>
                      <td className={toneClass(row.driftWeight)}>{fmtPct(row.driftWeight)}</td>
                      <td>{fmtQty(row.currentQuantity)}</td>
                      <td>{fmtQty(row.targetQuantity)}</td>
                      <td><span className={`paper-action-tag ${row.recommendedAction}`}>{actionLabel(row.recommendedAction)}</span></td>
                      <td className="bt-trade-reason">{row.reason ?? '—'}</td>
                    </tr>)}</tbody>
                  </table>
                </div>
              )}
            </section>

            <aside className="paper-bind-card">
              <div>
                <h3>策略绑定</h3>
                <p>{account.strategyVersionId ? '已绑定策略版本，可持续评估仓位偏差。' : '绑定策略版本后进入跟踪评估。'}</p>
              </div>
              <label>策略</label>
              <select className="bt-input" value={selectedStrategyId} onChange={(e) => setSelectedStrategyId(e.target.value)}>
                <option value="">选择策略</option>
                {strategies.map((strategy) => (
                  <option key={strategy.id} value={strategy.id}>{strategy.name} · {strategy.status}</option>
                ))}
              </select>
              <label>版本</label>
              <select className="bt-input" value={selectedVersionId} onChange={(e) => setSelectedVersionId(e.target.value)} disabled={!selectedStrategyDetail}>
                <option value="">选择版本</option>
                {selectedStrategyDetail?.versions.map((version) => (
                  <option key={version.id} value={version.id}>{version.version}</option>
                ))}
              </select>
              <button type="button" className="bt-btn" disabled={bindLoading || !selectedStrategyId || !selectedVersionId} onClick={() => void bindStrategy()}>
                {bindLoading ? '绑定中…' : account.strategyVersionId ? '更新绑定' : '绑定策略'}
              </button>
              {bindMessage && <div className="paper-bind-message">{bindMessage}</div>}
            </aside>
          </div>
        )}

        {view === 'performance' && (
          <section className="paper-performance-panel">
            <div className="paper-panel-head compact">
              <div>
                <h3>绩效与回撤</h3>
                <p>日结 NAV、收益与风险轨迹</p>
              </div>
              <div className="paper-performance-meta">
                <span>日收益 {fmtPct(latestNav?.dailyReturn)}</span>
                <span>最大回撤 {fmtPct(latestNav?.drawdown)}</span>
                <span>持仓市值 {latestNav ? fmtCny(latestNav.marketValue) : '—'}</span>
              </div>
            </div>
            {nav.length > 0 ? <NavChart data={nav} /> : <div className="paper-blotter-empty">暂无 NAV 轨迹，运行 EOD 后生成</div>}
          </section>
        )}
      </div>
    </div>
  )
}

// ── Main Screen ──────────────────────────────────────────────────────────────

export default function Paper({ initialAccountId }: PaperProps) {
  const [accounts, setAccounts] = useState<PaperAccount[]>([])
  const [selected, setSelected] = useState<string | null>(initialAccountId ?? null)
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadAccounts = useCallback(async () => {
    const list = await api.paper.listAccounts().catch(() => [] as PaperAccount[])
    setAccounts(list)
    setLoading(false)
    setSelected((prev) => prev ?? list[0]?.id ?? null)
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void loadAccounts() }, [loadAccounts])

  useEffect(() => {
    if (!initialAccountId) return
    if (accounts.some((a) => a.id === initialAccountId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelected(initialAccountId)
    } else if (!loading) {
      void loadAccounts()
    }
  }, [initialAccountId, accounts, loading, loadAccounts])

  const onCreated = (acc: PaperAccount) => {
    setAccounts((prev) => [acc, ...prev])
    setSelected(acc.id)
    setShowCreate(false)
  }
  const onAccountUpdated = (updated: PaperAccount) => {
    setAccounts((prev) => prev.map((account) => account.id === updated.id ? updated : account))
  }
  const selectedAccount = accounts.find((account) => account.id === selected)

  return (
    <div className="paper-terminal">
      <header className="paper-terminal-topbar">
        <div className="paper-terminal-brand">
          <h2>模拟交易台</h2>
          <span>Paper Trading · 策略跟踪 · 委托执行 · 风险复核</span>
        </div>
        <AccountSwitcher accounts={accounts} selectedId={selected} onSelect={setSelected} />
        <div className="paper-terminal-actions">
          <button type="button" className="bt-btn bt-btn-primary" onClick={() => setShowCreate(true)}>
            新建账户
          </button>
        </div>
      </header>

      <div className="paper-terminal-body">
        {loading ? (
          <div className="paper-empty">加载中…</div>
        ) : selectedAccount ? (
          <AccountDetail account={selectedAccount} onAccountUpdated={onAccountUpdated} />
        ) : (
          <div className="paper-empty">
            <div className="bt-empty-emoji">◎</div>
            <div className="bt-empty-title">创建第一个模拟账户</div>
            <div className="bt-empty-desc">绑定策略后运行 EOD，或在交易执行页手动下单</div>
            <button type="button" className="bt-btn bt-btn-primary" onClick={() => setShowCreate(true)}>新建账户</button>
          </div>
        )}
      </div>

      {showCreate && (
        <CreateAccountModal onClose={() => setShowCreate(false)} onCreated={onCreated} />
      )}
    </div>
  )
}
