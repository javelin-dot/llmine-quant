import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type MarketBarDailyOut, type SymbolStatsOut, type SymbolSummary } from '../../lib/api'

type SortKey = 'bars' | 'symbol' | 'recent'

const PAGE_SIZE = 10

function fmtNum(n: number, digits = 2): string {
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

function fmtVolume(v: number): string {
  if (!Number.isFinite(v) || v === 0) return '—'
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`
  return v.toLocaleString('en-US')
}

function fmtAmount(a: number | null | undefined): string {
  if (a == null || !Number.isFinite(a)) return '—'
  if (a >= 1e8) return `¥${(a / 1e8).toFixed(2)}亿`
  if (a >= 1e4) return `¥${(a / 1e4).toFixed(1)}万`
  return `¥${a.toFixed(0)}`
}

function daysBetween(start: string, end: string): number {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  if (!Number.isFinite(s) || !Number.isFinite(e)) return 0
  return Math.max(1, Math.round((e - s) / 86_400_000) + 1)
}

export interface LocalMarketLibraryProps {
  refreshKey?: number
}

export default function LocalMarketLibrary({ refreshKey }: LocalMarketLibraryProps) {
  // —— KPI(全库统计,不受分页影响) ——
  const [stats, setStats] = useState<SymbolStatsOut>({
    totalSymbols: 0,
    totalBars: 0,
    latestTradeDate: null,
    earliestTradeDate: null,
  })
  const [loadingStats, setLoadingStats] = useState(false)

  // —— 左侧:标的列表(分页) ——
  const [symbols, setSymbols] = useState<SymbolSummary[]>([])
  const [filter, setFilter] = useState('')
  const [debouncedFilter, setDebouncedFilter] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('bars')
  const [symbolsHasMore, setSymbolsHasMore] = useState(true)
  const [loadingSymbols, setLoadingSymbols] = useState(false)
  const symbolsLoadingRef = useRef(false)
  const symbolsScrollRef = useRef<HTMLDivElement | null>(null)
  const symbolsSentinelRef = useRef<HTMLDivElement | null>(null)

  // —— 右侧:K 线明细(分页) ——
  const [active, setActive] = useState<string | null>(null)
  const [bars, setBars] = useState<MarketBarDailyOut[]>([])
  const [barsHasMore, setBarsHasMore] = useState(true)
  const [loadingBars, setLoadingBars] = useState(false)
  const barsLoadingRef = useRef(false)
  const barsScrollRef = useRef<HTMLDivElement | null>(null)
  const barsSentinelRef = useRef<HTMLDivElement | null>(null)

  const [error, setError] = useState<string | null>(null)

  // “刷新名称”状态(主动从 AKShare 拉一次 stock_zh_a_spot 贴到 stock_info 表)
  const [refreshingNames, setRefreshingNames] = useState(false)
  const [namesToast, setNamesToast] = useState<string | null>(null)

  // 搜索框防抖 (250ms)
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedFilter(filter.trim()), 250)
    return () => window.clearTimeout(t)
  }, [filter])

  // —— 加载 KPI ——
  const loadStats = useCallback(() => {
    setLoadingStats(true)
    api.data
      .symbolsStats()
      .then(setStats)
      .catch(() => undefined)
      .finally(() => setLoadingStats(false))
  }, [])

  useEffect(() => {
    loadStats()
  }, [loadStats, refreshKey])

  // —— 加载首页/翻页 标的 ——
  const fetchSymbolsPage = useCallback(
    async (offset: number, append: boolean) => {
      if (symbolsLoadingRef.current) return
      symbolsLoadingRef.current = true
      setLoadingSymbols(true)
      setError(null)
      try {
        const rows = await api.data.symbols({
          search: debouncedFilter || undefined,
          sort: sortKey,
          offset,
          limit: PAGE_SIZE,
        })
        setSymbols((prev) => (append ? [...prev, ...rows] : rows))
        setSymbolsHasMore(rows.length === PAGE_SIZE)
        if (!append) {
          // 重置时切换默认选中第一行
          setActive(rows.length ? rows[0].symbol : null)
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        symbolsLoadingRef.current = false
        setLoadingSymbols(false)
      }
    },
    [debouncedFilter, sortKey],
  )

  // 搜索/排序/外部刷新 → 重置首页
  useEffect(() => {
    setSymbols([])
    setSymbolsHasMore(true)
    void fetchSymbolsPage(0, false)
    if (symbolsScrollRef.current) symbolsScrollRef.current.scrollTop = 0
  }, [fetchSymbolsPage, refreshKey])

  // 哨兵触发加载下一页
  useEffect(() => {
    const root = symbolsScrollRef.current
    const target = symbolsSentinelRef.current
    if (!root || !target) return
    const io = new IntersectionObserver(
      (entries) => {
        const ent = entries[0]
        if (
          ent.isIntersecting &&
          symbolsHasMore &&
          !symbolsLoadingRef.current
        ) {
          void fetchSymbolsPage(symbols.length, true)
        }
      },
      { root, rootMargin: '0px 0px 80px 0px', threshold: 0 },
    )
    io.observe(target)
    return () => io.disconnect()
  }, [fetchSymbolsPage, symbols.length, symbolsHasMore])

  // —— 加载首页/翻页 明细 bars ——
  const fetchBarsPage = useCallback(
    async (symbol: string, offset: number, append: boolean) => {
      if (barsLoadingRef.current) return
      barsLoadingRef.current = true
      setLoadingBars(true)
      try {
        const rows = await api.data.marketBars(symbol, undefined, undefined, PAGE_SIZE, offset, 'desc')
        setBars((prev) => (append ? [...prev, ...rows] : rows))
        setBarsHasMore(rows.length === PAGE_SIZE)
      } catch {
        if (!append) setBars([])
      } finally {
        barsLoadingRef.current = false
        setLoadingBars(false)
      }
    },
    [],
  )

  // 切标的或刷新 → 重置 bars
  useEffect(() => {
    if (!active) {
      setBars([])
      setBarsHasMore(false)
      return
    }
    setBars([])
    setBarsHasMore(true)
    void fetchBarsPage(active, 0, false)
    if (barsScrollRef.current) barsScrollRef.current.scrollTop = 0
  }, [active, fetchBarsPage, refreshKey])

  // 哨兵触发 bars 下一页
  useEffect(() => {
    const root = barsScrollRef.current
    const target = barsSentinelRef.current
    if (!root || !target || !active) return
    const io = new IntersectionObserver(
      (entries) => {
        const ent = entries[0]
        if (ent.isIntersecting && barsHasMore && !barsLoadingRef.current) {
          void fetchBarsPage(active, bars.length, true)
        }
      },
      { root, rootMargin: '0px 0px 80px 0px', threshold: 0 },
    )
    io.observe(target)
    return () => io.disconnect()
  }, [active, bars.length, barsHasMore, fetchBarsPage])

  const activeMeta = useMemo(
    () => symbols.find((s) => s.symbol === active) ?? null,
    [symbols, active],
  )

  const handleManualRefresh = useCallback(() => {
    loadStats()
    setSymbols([])
    setSymbolsHasMore(true)
    void fetchSymbolsPage(0, false)
  }, [loadStats, fetchSymbolsPage])

  const handleRefreshNames = useCallback(async () => {
    if (refreshingNames) return
    setRefreshingNames(true)
    setNamesToast(null)
    try {
      const res = await api.data.refreshStockInfo()
      setNamesToast(`已刷新 ${res.upserted.toLocaleString('en-US')} 个名称`)
      // 名称变了重拉首页让列表重新取
      setSymbols([])
      setSymbolsHasMore(true)
      void fetchSymbolsPage(0, false)
    } catch (e) {
      setNamesToast(`刷新名称失败:${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setRefreshingNames(false)
      window.setTimeout(() => setNamesToast(null), 4000)
    }
  }, [refreshingNames, fetchSymbolsPage])

  return (
    <section className="data-market-lib">
      <div className="dml-head">
        <div className="dml-head-title">
          <h4>本地行情库 · Local Market Library</h4>
          <span className="dml-sub">AKShare 落库后立即可用 · 用于回测与三步选股</span>
        </div>
        <div className="dml-head-kpis">
          <div className="dml-kpi">
            <small>标的数</small>
            <strong>{stats.totalSymbols.toLocaleString('en-US')}</strong>
          </div>
          <div className="dml-kpi">
            <small>总条数</small>
            <strong>{stats.totalBars.toLocaleString('en-US')}</strong>
          </div>
          <div className="dml-kpi">
            <small>最新交易日</small>
            <strong>{stats.latestTradeDate ?? '—'}</strong>
          </div>
          <button
            className="dml-refresh"
            onClick={handleManualRefresh}
            disabled={loadingStats || loadingSymbols}
          >
            {loadingStats || loadingSymbols ? '刷新中…' : '↻ 刷新'}
          </button>
          <button
            className="dml-refresh"
            onClick={handleRefreshNames}
            disabled={refreshingNames}
            title="从 AKShare 拉一次快照, 补齐/刷新股票中文名称"
          >
            {refreshingNames ? '拉取名称中…' : '名称库'}
          </button>
        </div>
      </div>

      {namesToast && <div className="bt-toast bt-toast-blue dml-toast">{namesToast}</div>}

      {error && <div className="bt-toast bt-toast-red dml-toast">{error}</div>}

      <div className="dml-body">
        {/* 左:标的列表(分页+无限滚动) */}
        <div className="dml-list-pane">
          <div className="dml-list-controls">
            <input
              className="bt-input dml-search"
              placeholder="搜索代码或名称（如 600519 / 贵州茅台）"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <div className="dml-sort">
              <button
                className={sortKey === 'bars' ? 'dml-sort-btn active' : 'dml-sort-btn'}
                onClick={() => setSortKey('bars')}
              >条数</button>
              <button
                className={sortKey === 'recent' ? 'dml-sort-btn active' : 'dml-sort-btn'}
                onClick={() => setSortKey('recent')}
              >最新</button>
              <button
                className={sortKey === 'symbol' ? 'dml-sort-btn active' : 'dml-sort-btn'}
                onClick={() => setSortKey('symbol')}
              >代码</button>
            </div>
          </div>

          {symbols.length === 0 && !loadingSymbols && (
            <div className="dml-empty">
              <strong>{debouncedFilter ? '无匹配代码' : '本地暂无行情数据'}</strong>
              {!debouncedFilter && (
                <p>展开上方「导入日线行情（AKShare）」拉取标的即可在此查看。</p>
              )}
            </div>
          )}

          <div className="dml-list" ref={symbolsScrollRef}>
            {symbols.map((s) => {
              const days = daysBetween(s.startDate, s.endDate)
              const density = s.bars / days
              return (
                <button
                  key={s.symbol}
                  className={active === s.symbol ? 'dml-row active' : 'dml-row'}
                  onClick={() => setActive(s.symbol)}
                >
                  <span className="dml-row-symbol">
                    {s.symbol}
                    {s.name && <em className="dml-row-name">{s.name}</em>}
                  </span>
                  <span className="dml-row-bars">
                    <strong>{s.bars.toLocaleString('en-US')}</strong>
                    <em>条</em>
                  </span>
                  <span className="dml-row-range">
                    {s.startDate} → {s.endDate}
                  </span>
                  <span className={`dml-row-density ${density > 0.6 ? 'ok' : 'warn'}`}>
                    {(density * 100).toFixed(0)}%覆盖
                  </span>
                </button>
              )
            })}
            {/* IntersectionObserver 哨兵 */}
            <div ref={symbolsSentinelRef} className="dml-sentinel" />
            {loadingSymbols && symbols.length > 0 && (
              <div className="dml-empty-mini">加载中…</div>
            )}
            {!loadingSymbols && !symbolsHasMore && symbols.length > 0 && (
              <div className="dml-empty-mini">— 已到底部 —</div>
            )}
          </div>
        </div>

        {/* 右:K 线表格(倒序+无限滚动) */}
        <div className="dml-detail-pane">
          {activeMeta ? (
            <div className="dml-detail-head">
              <div>
                <h5>
                  {activeMeta.symbol}
                  {activeMeta.name && (
                    <span className="dml-detail-name">{activeMeta.name}</span>
                  )}
                </h5>
                <span className="dml-detail-sub">
                  {activeMeta.bars.toLocaleString('en-US')} 条 ·
                  {' '}{activeMeta.startDate} → {activeMeta.endDate}
                </span>
              </div>
              <span className="dml-detail-meta">
                按交易日倒序 · 已加载 {bars.length}{barsHasMore ? '+' : ''} 条
              </span>
            </div>
          ) : (
            <div className="dml-detail-head">
              <h5>请选择一个标的</h5>
            </div>
          )}

          {bars.length > 0 && (
            <div className="dml-bars-wrap" ref={barsScrollRef}>
              <table className="dml-bars">
                <thead>
                  <tr>
                    <th>交易日</th>
                    <th className="num">开</th>
                    <th className="num">高</th>
                    <th className="num">低</th>
                    <th className="num">收</th>
                    <th className="num">涨跌</th>
                    <th className="num">成交量</th>
                    <th className="num">成交额</th>
                    <th>标记</th>
                  </tr>
                </thead>
                <tbody>
                  {bars.map((b) => {
                    const base = b.prevClose && b.prevClose > 0 ? b.prevClose : b.open
                    const chg = base > 0 ? (b.close - base) / base : 0
                    const tone = chg > 0 ? 'pos' : chg < 0 ? 'neg' : 'flat'
                    return (
                      <tr key={b.id}>
                        <td className="dml-bars-date">{b.tradeDate}</td>
                        <td className="num">{fmtNum(b.open)}</td>
                        <td className="num">{fmtNum(b.high)}</td>
                        <td className="num">{fmtNum(b.low)}</td>
                        <td className={`num ${tone}`}>{fmtNum(b.close)}</td>
                        <td className={`num ${tone}`}>{(chg * 100).toFixed(2)}%</td>
                        <td className="num">{fmtVolume(b.volume)}</td>
                        <td className="num">{fmtAmount(b.amount)}</td>
                        <td className="dml-bars-flags">
                          {b.isSt && <span className="dml-flag warn">ST</span>}
                          {b.isLimitUp && <span className="dml-flag up">涨停</span>}
                          {b.isLimitDown && <span className="dml-flag down">跌停</span>}
                          {b.isSuspended && <span className="dml-flag mute">停牌</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div ref={barsSentinelRef} className="dml-sentinel" />
              {loadingBars && (
                <div className="dml-empty-mini">加载中…</div>
              )}
              {!loadingBars && !barsHasMore && (
                <div className="dml-empty-mini">— 已到底部 —</div>
              )}
            </div>
          )}

          {bars.length === 0 && loadingBars && (
            <div className="dml-loading">读取行情中…</div>
          )}

          {!loadingBars && bars.length === 0 && active && (
            <div className="dml-empty-mini">该标的暂无本地行情</div>
          )}
        </div>
      </div>
    </section>
  )
}
