import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  api,
  type BacktestCreatePayload,
  type BacktestMetricPayload,
  type BacktestReportPayload,
  type BacktestTaskListPayload,
  type SensitivityRunPayload,
  type SymbolSummary,
  type WalkForwardFoldPayload,
} from '../../lib/api'
import EquityChart from './EquityChart'

interface BacktestProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
  initialStrategyId?: string
  initialTaskId?: string
}

type Segment = 'all' | 'is' | 'oos'
type ResultTab = 'overview' | 'walk-forward' | 'sensitivity' | 'trades' | 'overfit'

interface ConfigState {
  universe: string[]
  startDate: string
  endDate: string
  inSampleEndDate: string
  initialCash: number
  strategyName: string
  shortWindow: number
  longWindow: number
  targetGross: number
  maxPositions: number
  commissionRate: number
  minCommission: number
  stampTaxRate: number
  slippageBps: number
}

const DEFAULT_CONFIG: ConfigState = {
  universe: [],
  startDate: '',
  endDate: '',
  inSampleEndDate: '',
  initialCash: 1_000_000,
  strategyName: 'dual_ma',
  shortWindow: 5,
  longWindow: 20,
  targetGross: 0.95,
  maxPositions: 20,
  commissionRate: 0.0003,
  minCommission: 5,
  stampTaxRate: 0.001,
  slippageBps: 1,
}

function buildPayload(config: ConfigState): BacktestCreatePayload {
  return {
    universe: config.universe,
    startDate: config.startDate,
    endDate: config.endDate,
    inSampleEndDate: config.inSampleEndDate || undefined,
    initialCash: config.initialCash,
    strategyName: config.strategyName,
    strategyParams: {
      short_window: config.shortWindow,
      long_window: config.longWindow,
      target_gross: config.targetGross,
      max_positions: config.maxPositions,
    },
    costConfig: {
      commissionRate: config.commissionRate,
      minCommission: config.minCommission,
      stampTaxRate: config.stampTaxRate,
      slippageBps: config.slippageBps,
    },
  }
}

function pct(v: number | null | undefined, digits = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`
}

function num(v: number | null | undefined, digits = 2): string {
  if (v == null || !isFinite(v)) return '—'
  return v.toFixed(digits)
}

function toneFor(v: number | null | undefined, kind: 'return' | 'sharpe' | 'dd' | 'neutral'): string {
  if (v == null) return 'gray'
  if (kind === 'dd') return v <= -0.15 ? 'red' : v <= -0.05 ? 'yellow' : 'green'
  if (kind === 'sharpe') return v >= 1.5 ? 'green' : v >= 0.8 ? 'blue' : v >= 0 ? 'yellow' : 'red'
  if (kind === 'return') return v >= 0 ? 'green' : 'red'
  return 'blue'
}

export default function Backtest({ initialStrategyId, initialTaskId }: BacktestProps) {
  const [config, setConfig] = useState<ConfigState>(DEFAULT_CONFIG)
  const [symbols, setSymbols] = useState<SymbolSummary[]>([])
  const [history, setHistory] = useState<BacktestTaskListPayload[]>([])
  const [activeTaskId, setActiveTaskId] = useState<string | null>(initialTaskId ?? null)
  const [report, setReport] = useState<BacktestReportPayload | null>(null)
  const [segment, setSegment] = useState<Segment>('all')
  const [resultTab, setResultTab] = useState<ResultTab>('overview')
  const [running, setRunning] = useState<null | 'backtest' | 'walk-forward' | 'sensitivity'>(null)
  const [statusMsg, setStatusMsg] = useState<{ tone: 'green' | 'red' | 'blue'; text: string } | null>(null)
  const [showCost, setShowCost] = useState(false)
  const [showParams, setShowParams] = useState(false)

  // Load available symbols and run history on mount.
  useEffect(() => {
    void api.data.symbols().then((rows) => {
      setSymbols(rows)
      // Auto-populate config defaults from the local data corpus on first load.
      if (rows.length && !config.startDate) {
        const cover = pickCoverage(rows)
        setConfig((prev) => ({
          ...prev,
          universe: prev.universe.length ? prev.universe : rows.slice(0, Math.min(rows.length, 12)).map((r) => r.symbol),
          startDate: prev.startDate || cover.startDate,
          endDate: prev.endDate || cover.endDate,
        }))
      }
    })
    void refreshHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load active task report whenever activeTaskId changes.
  useEffect(() => {
    if (!activeTaskId) {
      setReport(null)
      return
    }
    void api.backtest.report(activeTaskId).then(setReport).catch((e) => {
      setStatusMsg({ tone: 'red', text: `加载报告失败: ${e instanceof Error ? e.message : String(e)}` })
    })
  }, [activeTaskId])

  // When jumping in with a strategyId, surface a hint (config presets are not yet
  // persisted on Strategy rows — leave to the user to confirm config).
  useEffect(() => {
    if (initialStrategyId && !initialTaskId) {
      setStatusMsg({
        tone: 'blue',
        text: `已为策略 ${initialStrategyId.slice(0, 8)}… 准备配置，按"运行回测"开始。`,
      })
    }
  }, [initialStrategyId, initialTaskId])

  const refreshHistory = useCallback(async () => {
    try {
      const list = await api.backtest.list(20)
      setHistory(list)
    } catch (e) {
      console.error('list backtests failed:', e)
    }
  }, [])

  const flash = (tone: 'green' | 'red' | 'blue', text: string, ms = 3500) => {
    setStatusMsg({ tone, text })
    setTimeout(() => setStatusMsg(null), ms)
  }

  const validate = (): string | null => {
    if (!config.universe.length) return '请至少选择一个标的'
    if (!config.startDate || !config.endDate) return '请填写起止日期'
    if (config.startDate > config.endDate) return '起止日期顺序有误'
    if (config.inSampleEndDate) {
      if (config.inSampleEndDate < config.startDate || config.inSampleEndDate >= config.endDate) {
        return 'IS 切分日必须在 [起始, 结束) 范围内'
      }
    }
    return null
  }

  const runBacktest = async () => {
    const err = validate()
    if (err) {
      flash('red', err)
      return
    }
    setRunning('backtest')
    setStatusMsg(null)
    try {
      const result = await api.backtest.runReal(buildPayload(config))
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `回测完成，task=${result.taskId.slice(0, 8)}…`)
      setResultTab('overview')
    } catch (e) {
      flash('red', `回测失败: ${e instanceof Error ? e.message : String(e)}`, 6000)
    } finally {
      setRunning(null)
    }
  }

  const runWalkForward = async () => {
    const err = validate()
    if (err) return flash('red', err)
    setRunning('walk-forward')
    try {
      const result = await api.backtest.walkForward({ ...buildPayload(config), folds: 4, trainRatio: 0.7 })
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `Walk-Forward 完成 (${result.folds.length} 折)`)
      setResultTab('walk-forward')
    } catch (e) {
      flash('red', `Walk-Forward 失败: ${e instanceof Error ? e.message : String(e)}`, 6000)
    } finally {
      setRunning(null)
    }
  }

  const runSensitivity = async () => {
    if (!activeTaskId) {
      flash('blue', '先运行一次回测，再做敏感性扫描')
      return
    }
    const err = validate()
    if (err) return flash('red', err)
    setRunning('sensitivity')
    try {
      const result = await api.backtest.sensitivity(buildPayload(config))
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `敏感性扫描完成 (${result.runs.length} 变体)`)
      setResultTab('sensitivity')
    } catch (e) {
      flash('red', `敏感性扫描失败: ${e instanceof Error ? e.message : String(e)}`, 6000)
    } finally {
      setRunning(null)
    }
  }

  const toggleSymbol = (symbol: string) => {
    setConfig((prev) => ({
      ...prev,
      universe: prev.universe.includes(symbol)
        ? prev.universe.filter((s) => s !== symbol)
        : [...prev.universe, symbol],
    }))
  }

  const selectAllSymbols = () => setConfig((prev) => ({ ...prev, universe: symbols.map((s) => s.symbol) }))
  const clearSymbols = () => setConfig((prev) => ({ ...prev, universe: [] }))

  const loadHistory = (item: BacktestTaskListPayload) => {
    setActiveTaskId(item.taskId)
    // Restore config from the picked task so re-runs are easy.
    setConfig((prev) => ({
      ...prev,
      universe: item.universe.length ? item.universe : prev.universe,
      startDate: item.startDate ?? prev.startDate,
      endDate: item.endDate ?? prev.endDate,
      inSampleEndDate: item.inSampleEndDate ?? '',
      strategyName: item.strategyName ?? prev.strategyName,
    }))
  }

  const segmentMetric: BacktestMetricPayload | null = useMemo(() => {
    if (!report?.summary.metrics) return null
    if (segment === 'is') return report.summary.inSampleMetrics
    if (segment === 'oos') return report.summary.outSampleMetrics
    return report.summary.metrics
  }, [report, segment])

  return (
    <div className="bt-workbench">
      <header className="bt-header">
        <div>
          <h2 className="bt-title">回测实验室</h2>
          <span className="bt-subtitle">真实日线行情 · 受控 DSL 策略 · IS/OOS / Walk-Forward / 敏感性 / 过拟合 / 解释</span>
        </div>
        <div className="bt-actions">
          <button
            className="bt-btn bt-btn-primary"
            disabled={running !== null}
            onClick={() => void runBacktest()}
          >
            {running === 'backtest' ? '回测中…' : '运行回测'}
          </button>
          <button className="bt-btn" disabled={running !== null} onClick={() => void runWalkForward()}>
            {running === 'walk-forward' ? '运行中…' : 'Walk-Forward'}
          </button>
          <button className="bt-btn" disabled={running !== null} onClick={() => void runSensitivity()}>
            {running === 'sensitivity' ? '运行中…' : '敏感性扫描'}
          </button>
        </div>
      </header>

      {statusMsg && (
        <div className={`bt-toast bt-toast-${statusMsg.tone}`}>{statusMsg.text}</div>
      )}

      <div className="bt-layout">
        {/* ── Left: Configuration ─────────────────────────────────── */}
        <aside className="bt-config">
          <div className="bt-config-section">
            <label className="bt-label">策略</label>
            <select
              className="bt-input"
              value={config.strategyName}
              onChange={(e) => setConfig({ ...config, strategyName: e.target.value })}
            >
              <option value="dual_ma">dual_ma（双均线）</option>
            </select>
          </div>

          <div className="bt-config-section">
            <div className="bt-label-row">
              <label className="bt-label">股票池 ({config.universe.length})</label>
              <div className="bt-chip-actions">
                <button className="bt-chip-btn" onClick={selectAllSymbols}>全选</button>
                <button className="bt-chip-btn" onClick={clearSymbols}>清空</button>
              </div>
            </div>
            <div className="bt-universe">
              {symbols.length === 0 ? (
                <div className="bt-empty-line">本地无可用行情，请先导入</div>
              ) : (
                symbols.map((s) => (
                  <button
                    key={s.symbol}
                    className={`bt-symbol-chip ${config.universe.includes(s.symbol) ? 'on' : ''}`}
                    onClick={() => toggleSymbol(s.symbol)}
                    title={`${s.bars} 根 · ${s.startDate} ~ ${s.endDate}`}
                  >
                    {s.symbol}
                    <span className="bt-symbol-bars">{s.bars}</span>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="bt-config-section">
            <label className="bt-label">日期范围</label>
            <div className="bt-row">
              <input
                type="date"
                className="bt-input"
                value={config.startDate}
                onChange={(e) => setConfig({ ...config, startDate: e.target.value })}
              />
              <span className="bt-row-sep">→</span>
              <input
                type="date"
                className="bt-input"
                value={config.endDate}
                onChange={(e) => setConfig({ ...config, endDate: e.target.value })}
              />
            </div>
          </div>

          <div className="bt-config-section">
            <label className="bt-label">IS 切分（可选）</label>
            <input
              type="date"
              className="bt-input"
              value={config.inSampleEndDate}
              onChange={(e) => setConfig({ ...config, inSampleEndDate: e.target.value })}
              placeholder="留空则不切分"
            />
            <div className="bt-hint">切分日（含）之前为样本内，之后为样本外</div>
          </div>

          <div className="bt-config-section">
            <label className="bt-label">初始资金</label>
            <input
              type="number"
              className="bt-input"
              value={config.initialCash}
              min={1000}
              step={10000}
              onChange={(e) => setConfig({ ...config, initialCash: Number(e.target.value) })}
            />
          </div>

          <div className="bt-config-section">
            <button className="bt-collapse" onClick={() => setShowParams((v) => !v)}>
              {showParams ? '▼' : '▸'} 策略参数
            </button>
            {showParams && (
              <div className="bt-params">
                <div className="bt-row">
                  <NumberField label="短窗口" value={config.shortWindow} onChange={(v) => setConfig({ ...config, shortWindow: v })} step={1} min={2} />
                  <NumberField label="长窗口" value={config.longWindow} onChange={(v) => setConfig({ ...config, longWindow: v })} step={1} min={3} />
                </div>
                <div className="bt-row">
                  <NumberField label="目标毛敞口" value={config.targetGross} onChange={(v) => setConfig({ ...config, targetGross: v })} step={0.05} min={0.1} max={1.0} />
                  <NumberField label="最大持仓数" value={config.maxPositions} onChange={(v) => setConfig({ ...config, maxPositions: v })} step={1} min={1} />
                </div>
              </div>
            )}
          </div>

          <div className="bt-config-section">
            <button className="bt-collapse" onClick={() => setShowCost((v) => !v)}>
              {showCost ? '▼' : '▸'} 成本配置
            </button>
            {showCost && (
              <div className="bt-params">
                <div className="bt-row">
                  <NumberField label="佣金率" value={config.commissionRate} onChange={(v) => setConfig({ ...config, commissionRate: v })} step={0.0001} />
                  <NumberField label="最低佣金" value={config.minCommission} onChange={(v) => setConfig({ ...config, minCommission: v })} step={1} min={0} />
                </div>
                <div className="bt-row">
                  <NumberField label="印花税" value={config.stampTaxRate} onChange={(v) => setConfig({ ...config, stampTaxRate: v })} step={0.0005} min={0} />
                  <NumberField label="滑点 bps" value={config.slippageBps} onChange={(v) => setConfig({ ...config, slippageBps: v })} step={0.5} min={0} />
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* ── Center: Results ─────────────────────────────────────── */}
        <main className="bt-result">
          {!report ? (
            <div className="bt-result-empty">
              <div className="bt-empty-emoji">↯</div>
              <div className="bt-empty-title">尚无结果</div>
              <div className="bt-empty-desc">配置股票池与日期后点击"运行回测"，或从右侧历史中选择一次回测载入</div>
            </div>
          ) : (
            <ResultView
              report={report}
              segment={segment}
              segmentMetric={segmentMetric}
              setSegment={setSegment}
              resultTab={resultTab}
              setResultTab={setResultTab}
            />
          )}
        </main>

        {/* ── Right: Run History ──────────────────────────────────── */}
        <aside className="bt-history">
          <div className="bt-history-head">
            <h4>运行历史</h4>
            <button className="bt-chip-btn" onClick={() => void refreshHistory()}>刷新</button>
          </div>
          <div className="bt-history-list">
            {history.length === 0 ? (
              <div className="bt-empty-line">尚无历史回测</div>
            ) : (
              history.map((h) => (
                <button
                  key={h.taskId}
                  className={`bt-history-item ${h.taskId === activeTaskId ? 'on' : ''}`}
                  onClick={() => loadHistory(h)}
                >
                  <div className="bt-history-row1">
                    <span className="bt-history-name">{h.strategyName ?? 'dual_ma'}</span>
                    <span className={`bt-history-status status-tag-${h.status === 'completed' ? 'green' : 'yellow'}`}>
                      {h.status}
                    </span>
                  </div>
                  <div className="bt-history-row2">
                    <span>{h.startDate ?? '?'} → {h.endDate ?? '?'}</span>
                  </div>
                  <div className="bt-history-row3">
                    <span className={`mini ${toneFor(h.cumulativeReturn, 'return') === 'green' ? 'pos' : 'neg'}`}>
                      {pct(h.cumulativeReturn, 1)}
                    </span>
                    <span className="mini">SR {num(h.sharpeRatio)}</span>
                    <span className="mini neg">{pct(h.maxDrawdown, 1)}</span>
                    {h.overfitLevel && (
                      <span className={`mini overfit-${h.overfitLevel}`}>{h.overfitLevel}</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}

// ── helpers ──────────────────────────────────────────────────────────────

function pickCoverage(symbols: SymbolSummary[]): { startDate: string; endDate: string } {
  let start = symbols[0].startDate
  let end = symbols[0].endDate
  for (const s of symbols) {
    if (s.startDate > start) start = s.startDate
    if (s.endDate < end) end = s.endDate
  }
  return { startDate: start, endDate: end }
}

interface NumberFieldProps {
  label: string
  value: number
  onChange: (v: number) => void
  step?: number
  min?: number
  max?: number
}

function NumberField({ label, value, onChange, step = 1, min, max }: NumberFieldProps) {
  return (
    <label className="bt-field">
      <span>{label}</span>
      <input
        type="number"
        className="bt-input small"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  )
}

interface ResultViewProps {
  report: BacktestReportPayload
  segment: Segment
  segmentMetric: BacktestMetricPayload | null
  setSegment: (s: Segment) => void
  resultTab: ResultTab
  setResultTab: (t: ResultTab) => void
}

function ResultView({ report, segment, segmentMetric, setSegment, resultTab, setResultTab }: ResultViewProps) {
  const hasSplit = Boolean(report.summary.inSampleEndDate && report.summary.inSampleMetrics)
  return (
    <>
      <div className="bt-summary-head">
        <div>
          <span className="bt-summary-label">回测任务</span>
          <code className="bt-summary-id">{report.taskId.slice(0, 12)}…</code>
        </div>
        {hasSplit && (
          <div className="bt-segment-toggle">
            <button className={segment === 'all' ? 'on' : ''} onClick={() => setSegment('all')}>全段</button>
            <button className={segment === 'is' ? 'on' : ''} onClick={() => setSegment('is')}>样本内</button>
            <button className={segment === 'oos' ? 'on' : ''} onClick={() => setSegment('oos')}>样本外</button>
          </div>
        )}
      </div>

      <MetricsStrip metric={segmentMetric} />

      <div className="bt-tabs">
        {([
          ['overview', '总览'],
          ['walk-forward', `Walk-Forward${report.walkForwardFolds.length ? ` (${report.walkForwardFolds.length})` : ''}`],
          ['sensitivity', `敏感性${report.sensitivityRuns.length ? ` (${report.sensitivityRuns.length})` : ''}`],
          ['trades', `成交${report.trades.length ? ` (${report.trades.length})` : ''}`],
          ['overfit', '过拟合'],
        ] as [ResultTab, string][]).map(([tab, label]) => (
          <button
            key={tab}
            className={`bt-tab ${resultTab === tab ? 'on' : ''}`}
            onClick={() => setResultTab(tab)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="bt-tab-body">
        {resultTab === 'overview' && (
          <EquityChart equity={report.summary.equityCurve} inSampleEndDate={report.summary.inSampleEndDate} />
        )}
        {resultTab === 'walk-forward' && <WalkForwardView folds={report.walkForwardFolds} />}
        {resultTab === 'sensitivity' && <SensitivityView runs={report.sensitivityRuns} />}
        {resultTab === 'trades' && <TradesView trades={report.trades} />}
        {resultTab === 'overfit' && <OverfitView overfit={report.overfit} />}
      </div>
    </>
  )
}

function MetricsStrip({ metric }: { metric: BacktestMetricPayload | null }) {
  if (!metric) return <div className="bt-metrics-empty">无可用指标</div>
  const items: { label: string; value: string; tone: string }[] = [
    { label: '累计收益', value: pct(metric.cumulativeReturn), tone: toneFor(metric.cumulativeReturn, 'return') },
    { label: '年化收益', value: pct(metric.annualReturn), tone: toneFor(metric.annualReturn, 'return') },
    { label: '最大回撤', value: pct(metric.maxDrawdown), tone: toneFor(metric.maxDrawdown, 'dd') },
    { label: 'Sharpe', value: num(metric.sharpeRatio), tone: toneFor(metric.sharpeRatio, 'sharpe') },
    { label: '胜率', value: pct(metric.winRate, 1), tone: 'blue' },
    { label: '换手', value: num(metric.turnover), tone: 'blue' },
  ]
  return (
    <div className="bt-metrics-strip">
      {items.map((m) => (
        <div key={m.label} className={`bt-metric tone-${m.tone}`}>
          <span className="bt-metric-label">{m.label}</span>
          <span className="bt-metric-value">{m.value}</span>
        </div>
      ))}
    </div>
  )
}

function WalkForwardView({ folds }: { folds: WalkForwardFoldPayload[] }) {
  if (!folds.length) {
    return <div className="bt-empty-line">本任务没有 Walk-Forward 记录。在配置面板点击 "Walk-Forward" 运行。</div>
  }
  return (
    <table className="bt-table">
      <thead>
        <tr>
          <th>折</th>
          <th>训练区间</th>
          <th>训练收益</th>
          <th>训练 Sharpe</th>
          <th>测试区间</th>
          <th>测试收益</th>
          <th>测试 Sharpe</th>
          <th>测试回撤</th>
        </tr>
      </thead>
      <tbody>
        {folds.map((f) => (
          <tr key={f.foldIndex}>
            <td>#{f.foldIndex + 1}</td>
            <td className="bt-date">{f.trainStart} → {f.trainEnd}</td>
            <td className={f.trainReturn >= 0 ? 'pos' : 'neg'}>{pct(f.trainReturn)}</td>
            <td>{num(f.trainSharpe)}</td>
            <td className="bt-date">{f.testStart} → {f.testEnd}</td>
            <td className={f.testReturn >= 0 ? 'pos' : 'neg'}>{pct(f.testReturn)}</td>
            <td>{num(f.testSharpe)}</td>
            <td className="neg">{pct(f.testMaxDd)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function SensitivityView({ runs }: { runs: SensitivityRunPayload[] }) {
  if (!runs.length) {
    return <div className="bt-empty-line">本任务没有敏感性记录。在配置面板点击 "敏感性扫描" 运行。</div>
  }
  const params = runs.filter((r) => r.kind === 'param')
  const slippage = runs.filter((r) => r.kind === 'slippage')
  return (
    <div className="bt-sens">
      <SensitivityTable title="参数扰动" runs={params} />
      <SensitivityTable title="滑点扫描" runs={slippage} />
    </div>
  )
}

function SensitivityTable({ title, runs }: { title: string; runs: SensitivityRunPayload[] }) {
  if (!runs.length) return null
  return (
    <div className="bt-sens-block">
      <h5>{title}</h5>
      <table className="bt-table">
        <thead>
          <tr>
            <th>变体</th>
            <th>累计收益</th>
            <th>Sharpe</th>
            <th>最大回撤</th>
            <th>胜率</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr key={`${r.kind}-${i}`} className={r.isBaseline ? 'bt-baseline' : ''}>
              <td>{r.isBaseline ? '★ baseline' : r.label}</td>
              <td className={r.cumulativeReturn >= 0 ? 'pos' : 'neg'}>{pct(r.cumulativeReturn)}</td>
              <td>{num(r.sharpeRatio)}</td>
              <td className="neg">{pct(r.maxDrawdown)}</td>
              <td>{pct(r.winRate, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TradesView({ trades }: { trades: BacktestReportPayload['trades'] }) {
  if (!trades.length) return <div className="bt-empty-line">本任务没有成交。</div>
  return (
    <table className="bt-table">
      <thead>
        <tr>
          <th>日期</th>
          <th>标的</th>
          <th>方向</th>
          <th>数量</th>
          <th>价格</th>
          <th>金额</th>
          <th>目标权重</th>
          <th>触发原因</th>
        </tr>
      </thead>
      <tbody>
        {trades.map((t, i) => (
          <tr key={`${t.tradeDate}-${i}`}>
            <td className="bt-date">{t.tradeDate}</td>
            <td>{t.symbol}</td>
            <td className={t.side === 'buy' ? 'pos' : 'neg'}>{t.side.toUpperCase()}</td>
            <td>{num(t.quantity, 2)}</td>
            <td>{num(t.price, 4)}</td>
            <td>{num(t.amount, 2)}</td>
            <td>{pct(t.targetWeight)}</td>
            <td className="bt-trade-reason">{t.reason ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function OverfitView({ overfit }: { overfit: BacktestReportPayload['overfit'] }) {
  if (!overfit) return <div className="bt-empty-line">尚未计算过拟合评分。</div>
  return (
    <div className="bt-overfit">
      <div className={`bt-overfit-score overfit-${overfit.level}`}>
        <div className="bt-overfit-value">{overfit.score}</div>
        <div className="bt-overfit-label">/ 100 · {overfit.level === 'low' ? '低过拟合风险' : overfit.level === 'medium' ? '中等过拟合风险' : '高过拟合风险'}</div>
      </div>
      <table className="bt-table">
        <thead>
          <tr>
            <th>组件</th>
            <th>分数</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          {overfit.components.map((c) => (
            <tr key={c.name}>
              <td>{c.name}</td>
              <td className={c.score >= 0.7 ? 'pos' : c.score >= 0.4 ? '' : 'neg'}>{c.score.toFixed(2)}</td>
              <td className="bt-trade-reason">{c.detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
