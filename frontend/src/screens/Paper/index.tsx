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

  return <div ref={ref} style={{ width: '100%', height: 240 }} />
}

// ── Account Card ─────────────────────────────────────────────────────────────

function AccountCard({ account, active, onClick }: { account: PaperAccount; active: boolean; onClick: () => void }) {
  const pnlPct = account.peakNav != null && account.initialCash > 0
    ? (account.cash - account.initialCash) / account.initialCash
    : null
  return (
    <button className={`paper-account-card ${active ? 'on' : ''}`} onClick={onClick}>
      <div className="paper-account-name">{account.name}</div>
      <div className="paper-account-meta">
        <span className="status-tag-blue">{account.market}</span>
        <span className={`status-tag-${account.status === 'active' ? 'green' : account.status === 'paused' ? 'yellow' : 'gray'}`}>{account.status}</span>
        <span className={`status-tag-${account.strategyVersionId ? 'green' : 'gray'}`}>{account.strategyVersionId ? 'bound' : 'unbound'}</span>
      </div>
      <div className="paper-account-kpis">
        <div>
          <div className="paper-kpi-label">初始资金</div>
          <div className="paper-kpi-value">{fmtCny(account.initialCash)}</div>
        </div>
        <div>
          <div className="paper-kpi-label">现金</div>
          <div className="paper-kpi-value">{fmtCny(account.cash)}</div>
        </div>
        <div>
          <div className="paper-kpi-label">总收益</div>
          <div className={`paper-kpi-value ${toneClass(pnlPct)}`}>{fmtPct(pnlPct)}</div>
        </div>
      </div>
      <div className="paper-account-date">{account.lastProcessedDate ?? '未开始'}</div>
    </button>
  )
}

// ── Create Account Form ──────────────────────────────────────────────────────

function CreateAccountForm({ onCreated }: { onCreated: (a: PaperAccount) => void }) {
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
    <div className="paper-create-form">
      <h4 className="paper-form-title">新建模拟账户</h4>
      <div className="paper-form-row">
        <label className="paper-form-label">名称</label>
        <input className="bt-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="如：MA趋势模拟盘" />
      </div>
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
      <div className="paper-form-row">
        <label className="paper-form-label">开始日期</label>
        <input type="date" className="bt-input" value={form.inceptionDate ?? ''}
          onChange={(e) => setForm({ ...form, inceptionDate: e.target.value })} />
      </div>
      {error && <div className="bt-toast bt-toast-red">{error}</div>}
      <button className="bt-btn bt-btn-primary" disabled={loading} onClick={() => void submit()}>
        {loading ? '创建中…' : '创建账户'}
      </button>
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

  return (
    <div className="paper-console">
      <header className="paper-console-header">
        <div>
          <div className="paper-console-eyebrow">Paper Account</div>
          <h3>{account.name}</h3>
          <p>
            {selectedStrategyDetail?.name ?? '未绑定策略'}
            {selectedStrategyDetail && selectedVersionId ? ` · ${selectedStrategyDetail.versions.find((version) => version.id === selectedVersionId)?.version ?? '未选版本'}` : ''}
          </p>
        </div>
        <div className="paper-console-actions">
          <span className={`status-tag-${account.strategyVersionId ? 'green' : 'gray'}`}>{account.strategyVersionId ? 'tracking' : 'unbound'}</span>
          <span className={`status-tag-${account.status === 'active' ? 'green' : 'yellow'}`}>{account.status}</span>
          <input type="date" className="bt-input small" value={eodDate}
            onChange={(e) => setEodDate(e.target.value)} />
          <button className="bt-btn" disabled={eodLoading} onClick={() => void runEod()}>
            {eodLoading ? 'EOD 运行中…' : '运行 EOD'}
          </button>
        </div>
      </header>

      {eodResult && (
        <div className="bt-toast bt-toast-green">
          EOD {eodResult.tradeDate} 完成 · 下单 {eodResult.ordersCreated} · 成交 {eodResult.ordersFilled} · 拒绝 {eodResult.ordersRejected} · NAV {fmtCny(eodResult.nav)}
        </div>
      )}
      {eodError && <div className="bt-toast bt-toast-red">{eodError}</div>}

      <div className="paper-section-tabs">
        <button className={view === 'overview' ? 'active' : ''} onClick={() => setView('overview')}>账户概览</button>
        <button className={view === 'trading' ? 'active' : ''} onClick={() => setView('trading')}>交易执行</button>
        <button className={view === 'performance' ? 'active' : ''} onClick={() => setView('performance')}>绩效分析</button>
      </div>

      <div className="paper-overview-grid">
        <div>
          <span>当前 NAV</span>
          <strong className="tone-green">{latestNav ? fmtCny(latestNav.nav) : fmtCny(account.initialCash)}</strong>
        </div>
        <div>
          <span>现金</span>
          <strong>{latestNav ? fmtCny(latestNav.cash) : fmtCny(account.cash)}</strong>
        </div>
        <div>
          <span>当前仓位</span>
          <strong>{fmtPct(evaluation?.currentGross ?? grossExposure)}</strong>
        </div>
        <div>
          <span>目标仓位</span>
          <strong>{fmtPct(evaluation?.targetGross)}</strong>
        </div>
        <div>
          <span>仓位偏差</span>
          <strong>{fmtPct(evaluation?.driftGross)}</strong>
        </div>
        <div>
          <span>交易阶段</span>
          <strong>{sessionLabel(evaluation?.sessionStatus)}</strong>
        </div>
      </div>

      <div className="paper-view-shell">
        {view === 'overview' && (
          <div className="paper-overview-view">
            <section className="paper-target-panel">
            <div className="paper-panel-head">
              <div>
                <h3>目标仓位与偏差</h3>
                <p>
                  {!evaluation?.strategyBound
                    ? '尚未绑定策略，绑定策略版本后生成目标仓位与偏差评估'
                    : evaluation?.tradeDate
                      ? `基于 ${evaluation.tradeDate} 最新可用行情快照`
                      : '暂无可用行情快照'}
                </p>
              </div>
            </div>
            {!evaluation || evaluation.targets.length === 0 ? (
              <div className="bt-empty-line">
                {!evaluation?.strategyBound ? '未绑定策略，暂无目标仓位' : '暂无目标仓位'}
              </div>
            ) : (
              <div className="paper-table-scroll">
              <table className="bt-table">
                <thead><tr><th>标的</th><th>当前权重</th><th>目标权重</th><th>偏差</th><th>当前数量</th><th>目标数量</th><th>建议动作</th><th>依据</th></tr></thead>
                <tbody>{evaluation.targets.map((row)=><tr key={row.symbol}>
                  <td>{row.symbol}</td>
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

            <section className="paper-bind-panel paper-bind-card">
              <div>
                <h3>策略绑定</h3>
                <p>{account.strategyVersionId ? '当前账户已绑定策略版本，可持续评估仓位偏差。' : '先绑定策略版本，再让账户进入跟踪评估状态。'}</p>
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
              <button className="bt-btn" disabled={bindLoading || !selectedStrategyId || !selectedVersionId} onClick={() => void bindStrategy()}>
                {bindLoading ? '绑定中…' : account.strategyVersionId ? '更新绑定' : '绑定策略'}
              </button>
              {bindMessage && <div className="paper-bind-message">{bindMessage}</div>}
            </section>
          </div>
        )}

        {view === 'trading' && (
          <div className="paper-trading-view">
            <section className="paper-blotter-panel">
            <div className="paper-panel-head compact">
              <div>
                <h3>交易工作区</h3>
                <p>持仓、活动委托与风控复核</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="bt-tabs">
              <button className={`bt-tab ${tab === 'positions' ? 'on' : ''}`} onClick={() => setTab('positions')}>
                持仓 ({positions.length})
              </button>
              <button className={`bt-tab ${tab === 'orders' ? 'on' : ''}`} onClick={() => setTab('orders')}>
                委托 ({orders.length})
              </button>
              <button className={`bt-tab ${tab === 'breaches' ? 'on' : ''}`} onClick={() => setTab('breaches')}>
                风控 {breaches.length > 0 && <span className="paper-breach-badge">{breaches.length}</span>}
              </button>
            </div>

            <div className="bt-tab-body">
        {tab === 'positions' && (
          positions.length === 0 ? (
            <div className="bt-empty-line">暂无持仓（运行 EOD 后生成信号）</div>
          ) : (
            <table className="bt-table">
              <thead>
                <tr><th>标的</th><th>总持仓</th><th>可卖</th><th>今日买入</th><th>均价</th><th>最新价</th><th>市值</th><th>权重</th><th>操作</th></tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.symbol}>
                    <td>{p.symbol}</td>
                    <td>{fmtQty(p.quantity)}</td>
                    <td>{fmtQty(p.availableQuantity)}</td>
                    <td>{fmtQty(p.todayBuyQuantity)}</td>
                    <td>{fmtCny(p.avgCost)}</td>
                    <td>{p.lastPrice != null ? fmtCny(p.lastPrice) : '—'}</td>
                    <td>{fmtCny(p.marketValue)}</td>
                    <td>{fmtPct(p.weight)}</td>
                    <td>
                      <div className="paper-row-actions">
                        <button onClick={()=>quickSubmit(p.symbol,'buy',100)}>加仓</button>
                        <button disabled={p.availableQuantity <= 0} onClick={()=>quickSubmit(p.symbol,'sell',Math.min(100,p.availableQuantity))}>减仓</button>
                        <button disabled={p.availableQuantity <= 0} onClick={()=>quickSubmit(p.symbol,'sell',p.availableQuantity)}>平仓</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
        {tab === 'orders' && (
          orders.length === 0 ? (
            <div className="bt-empty-line">暂无订单</div>
          ) : (
            <>
              <div className="paper-order-toolbar">
                <div className="paper-order-filters">
                  <button className={orderFilter === 'all' ? 'active' : ''} onClick={() => setOrderFilter('all')}>全部</button>
                  <button className={orderFilter === 'open' ? 'active' : ''} onClick={() => setOrderFilter('open')}>活动委托</button>
                  <button className={orderFilter === 'done' ? 'active' : ''} onClick={() => setOrderFilter('done')}>已结束</button>
                </div>
                <button className="bt-btn" disabled={matchLoading || !orders.some((o) => ['pending', 'approved'].includes(o.status))} onClick={() => void matchOrders()}>
                  {matchLoading ? '撮合中…' : '撮合活动委托'}
                </button>
              </div>
              <table className="bt-table">
                <thead>
                  <tr><th>日期</th><th>标的</th><th>方向</th><th>委托数量</th><th>成交数量</th><th>剩余</th><th>状态</th><th>原因</th><th>操作</th></tr>
                </thead>
                <tbody>
                  {visibleOrders.slice(0, 50).map((o) => (
                  <tr key={o.id}>
                    <td className="bt-date">{o.tradeDate}</td>
                    <td>{o.symbol}</td>
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
                          <button onClick={() => startReplace(o)}>改单</button>
                          <button onClick={() => void cancelOrder(o)}>撤单</button>
                        </div>
                      ) : '—'}
                    </td>
                  </tr>
                  ))}
                </tbody>
              </table>
            </>
          )
        )}
        {tab === 'breaches' && (
          breaches.length === 0 ? (
            <div className="bt-empty-line">无风控触发</div>
          ) : (
            <table className="bt-table">
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
          )
        )}
      </div>
          </section>

            <aside className="paper-trade-panel">
              <div>
                <h3>模拟交易</h3>
                <p>支持即时撮合或先挂单再撮合，保留 A 股 T+1 与 100 股整数手约束。</p>
              </div>
              {editingOrderId && (
                <div className="paper-replace-banner">
                  正在改单
                  <button onClick={() => setEditingOrderId(null)}>退出</button>
                </div>
              )}
              <label>标的</label>
              <input className="bt-input" disabled={!!editingOrderId} placeholder="600519.SH" value={tradeForm.symbol} onChange={e=>setTradeForm((v)=>({...v,symbol:e.target.value}))} />
              <label>方向</label>
              <div className="paper-side-toggle">
                <button disabled={!!editingOrderId} className={tradeForm.side==='buy'?'active':''} onClick={()=>setTradeForm((v)=>({...v,side:'buy'}))}>买入 / 建仓</button>
                <button disabled={!!editingOrderId} className={tradeForm.side==='sell'?'active':''} onClick={()=>setTradeForm((v)=>({...v,side:'sell'}))}>卖出 / 减仓</button>
              </div>
              {!editingOrderId && (
                <>
                  <label>执行方式</label>
                  <div className="paper-side-toggle">
                    <button className={tradeForm.executionMode==='immediate'?'active':''} onClick={()=>setTradeForm((v)=>({...v,executionMode:'immediate'}))}>即时撮合</button>
                    <button className={tradeForm.executionMode==='queue'?'active':''} onClick={()=>setTradeForm((v)=>({...v,executionMode:'queue'}))}>先挂委托</button>
                  </div>
                </>
              )}
              <label>数量</label>
              <input type="number" min={1} step={tradeForm.side==='buy'?100:1} className="bt-input" value={tradeForm.quantity} onChange={e=>setTradeForm((v)=>({...v,quantity:Number(e.target.value)}))} />
              <button className="bt-btn bt-btn-primary" disabled={tradeLoading} onClick={()=>void submitTrade()}>
                {tradeLoading ? '提交中…' : editingOrderId ? '确认改单' : tradeForm.executionMode === 'queue' ? '提交委托' : '提交并撮合'}
              </button>
              {tradeMessage && <div className="paper-trade-message">{tradeMessage}</div>}
              <div className="paper-trade-note">
                <strong>A 股校验</strong>
                <span>买入按 100 股整数手向下取整</span>
                <span>卖出受 T+1 可卖数量约束</span>
                <span>风控继续执行单票仓位与现金底线检查</span>
              </div>
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
            {nav.length > 0 ? <NavChart data={nav} /> : <div className="bt-empty-line">暂无 NAV 轨迹，运行 EOD 后生成</div>}
          </section>
        )}
      </div>
    </div>
  )
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

  // Honor late-arriving initialAccountId (e.g. account was just created in
  // another screen and we navigated here). Switch only if it exists in the list,
  // and re-fetch when it's missing so freshly created accounts surface.
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
    <div className="paper-root">
      <header className="paper-header">
        <div>
          <h2 className="paper-title">模拟交易台</h2>
          <span className="paper-subtitle">Paper Trading Console · 策略跟踪 · 委托执行 · 风险复核</span>
        </div>
        <button className="bt-btn bt-btn-primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? '取消' : '新建账户'}
        </button>
      </header>

      <div className="paper-layout">
        {/* Account list */}
        <aside className="paper-sidebar">
          <div className="paper-sidebar-head">
            <span>Accounts</span>
            <strong>{accounts.length}</strong>
          </div>
          {showCreate && <CreateAccountForm onCreated={onCreated} />}
          {loading ? (
            <div className="bt-empty-line">加载中…</div>
          ) : accounts.length === 0 ? (
            <div className="bt-empty-line">暂无账户，点击"新建账户"开始</div>
          ) : (
            accounts.map((acc) => (
              <AccountCard
                key={acc.id}
                account={acc}
                active={selected === acc.id}
                onClick={() => setSelected(acc.id)}
              />
            ))
          )}
        </aside>

        {/* Detail panel */}
        <main className="paper-main">
          {selectedAccount ? (
            <AccountDetail account={selectedAccount} onAccountUpdated={onAccountUpdated} />
          ) : (
            <div className="paper-empty">
              <div className="bt-empty-emoji">◎</div>
              <div className="bt-empty-title">选择或创建模拟账户</div>
              <div className="bt-empty-desc">在左侧新建账户，配置策略后运行每日 EOD 进行模拟交易</div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
