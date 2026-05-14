import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  type PaperAccount,
  type PaperAccountCreatePayload,
  type PaperNavPoint,
  type PaperOrder,
  type PaperPosition,
  type PaperRiskBreach,
  type RunEodSummary,
} from '../../lib/api'
import * as echarts from 'echarts'

interface PaperProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

function fmtPct(v: number | null | undefined, d = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(d)}%`
}

function fmtCny(v: number | null | undefined): string {
  if (v == null) return '—'
  return `¥${v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
}
const EMPTY_DETAIL: DetailState = { nav: [], positions: [], orders: [], breaches: [] }

function AccountDetail({ accountId }: { accountId: string }) {
  const [detail, setDetail] = useState<DetailState>(EMPTY_DETAIL)
  const [tab, setTab] = useState<'positions' | 'orders' | 'breaches'>('positions')
  const [eodDate, setEodDate] = useState(new Date().toISOString().slice(0, 10))
  const [eodLoading, setEodLoading] = useState(false)
  const [eodResult, setEodResult] = useState<RunEodSummary | null>(null)
  const [eodError, setEodError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const [nav, positions, orders, breaches] = await Promise.all([
      api.paper.nav(accountId).catch(() => []),
      api.paper.positions(accountId).catch(() => []),
      api.paper.orders(accountId).catch(() => []),
      api.paper.breaches(accountId).catch(() => []),
    ])
    setDetail({
      nav: nav as PaperNavPoint[],
      positions: positions as PaperPosition[],
      orders: orders as PaperOrder[],
      breaches: breaches as PaperRiskBreach[],
    })
  }, [accountId])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load() }, [load])
  const { nav, positions, orders, breaches } = detail

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

  return (
    <div className="paper-detail">
      {/* NAV strip */}
      <div className="paper-nav-strip">
        <div className="paper-nav-kpi">
          <div className="paper-kpi-label">当前 NAV</div>
          <div className="paper-kpi-value tone-green">{latestNav ? fmtCny(latestNav.nav) : '—'}</div>
        </div>
        <div className="paper-nav-kpi">
          <div className="paper-kpi-label">现金</div>
          <div className="paper-kpi-value">{latestNav ? fmtCny(latestNav.cash) : '—'}</div>
        </div>
        <div className="paper-nav-kpi">
          <div className="paper-kpi-label">持仓市值</div>
          <div className="paper-kpi-value">{latestNav ? fmtCny(latestNav.marketValue) : '—'}</div>
        </div>
        <div className="paper-nav-kpi">
          <div className="paper-kpi-label">日收益</div>
          <div className={`paper-kpi-value ${toneClass(latestNav?.dailyReturn)}`}>
            {fmtPct(latestNav?.dailyReturn)}
          </div>
        </div>
        <div className="paper-nav-kpi">
          <div className="paper-kpi-label">最大回撤</div>
          <div className="paper-kpi-value neg">{fmtPct(latestNav?.drawdown)}</div>
        </div>
        <div className="paper-eod-block">
          <input type="date" className="bt-input small" value={eodDate}
            onChange={(e) => setEodDate(e.target.value)} />
          <button className="bt-btn" disabled={eodLoading} onClick={() => void runEod()}>
            {eodLoading ? 'EOD 运行中…' : '运行 EOD'}
          </button>
        </div>
      </div>

      {eodResult && (
        <div className="bt-toast bt-toast-green">
          EOD {eodResult.tradeDate} 完成 · 下单 {eodResult.ordersCreated} · 成交 {eodResult.ordersFilled} · 拒绝 {eodResult.ordersRejected} · NAV {fmtCny(eodResult.nav)}
        </div>
      )}
      {eodError && <div className="bt-toast bt-toast-red">{eodError}</div>}

      {/* NAV Chart */}
      {nav.length > 0 && <NavChart data={nav} />}

      {/* Tabs */}
      <div className="bt-tabs">
        <button className={`bt-tab ${tab === 'positions' ? 'on' : ''}`} onClick={() => setTab('positions')}>
          持仓 ({positions.length})
        </button>
        <button className={`bt-tab ${tab === 'orders' ? 'on' : ''}`} onClick={() => setTab('orders')}>
          订单 ({orders.length})
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
                <tr><th>标的</th><th>数量</th><th>均价</th><th>最新价</th><th>市值</th><th>权重</th></tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.symbol}>
                    <td>{p.symbol}</td>
                    <td>{p.quantity}</td>
                    <td>{fmtCny(p.avgCost)}</td>
                    <td>{p.lastPrice != null ? fmtCny(p.lastPrice) : '—'}</td>
                    <td>{fmtCny(p.marketValue)}</td>
                    <td>{fmtPct(p.weight)}</td>
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
            <table className="bt-table">
              <thead>
                <tr><th>日期</th><th>标的</th><th>方向</th><th>目标数量</th><th>成交数量</th><th>状态</th><th>原因</th></tr>
              </thead>
              <tbody>
                {orders.slice(0, 50).map((o) => (
                  <tr key={o.id}>
                    <td className="bt-date">{o.tradeDate}</td>
                    <td>{o.symbol}</td>
                    <td className={o.side === 'buy' ? 'pos' : 'neg'}>{o.side.toUpperCase()}</td>
                    <td>{o.targetQuantity}</td>
                    <td>{o.filledQuantity}</td>
                    <td>
                      <span className={`status-tag-${o.status === 'filled' ? 'green' : o.status === 'rejected' ? 'red' : 'yellow'}`}>
                        {o.status}
                      </span>
                    </td>
                    <td className="bt-trade-reason">{o.rejectionReason ?? o.reason ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
    </div>
  )
}

// ── Main Screen ──────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function Paper(_props: PaperProps) {
  const [accounts, setAccounts] = useState<PaperAccount[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  const loadAccounts = useCallback(async () => {
    const list = await api.paper.listAccounts().catch(() => [] as PaperAccount[])
    setAccounts(list)
    setLoading(false)
    if (list.length) setSelected((prev) => prev ?? list[0].id)
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void loadAccounts() }, [loadAccounts])

  const onCreated = (acc: PaperAccount) => {
    setAccounts((prev) => [acc, ...prev])
    setSelected(acc.id)
    setShowCreate(false)
  }

  return (
    <div className="paper-root">
      <header className="paper-header">
        <div>
          <h2 className="paper-title">模拟盘</h2>
          <span className="paper-subtitle">Paper Trading · 日结 EOD · T+1 撮合 · 风控校验</span>
        </div>
        <button className="bt-btn bt-btn-primary" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? '取消' : '新建账户'}
        </button>
      </header>

      <div className="paper-layout">
        {/* Account list */}
        <aside className="paper-sidebar">
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
          {selected ? (
            <AccountDetail accountId={selected} />
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
