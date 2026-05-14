import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  api,
  type BacktestCreatePayload,
  type BacktestMetricPayload,
  type BacktestReportPayload,
  type BacktestTaskListPayload,
  type SensitivityRunPayload,
  type StrategyListItem,
  type SymbolSummary,
  type UniverseSuggestResult,
  type WalkForwardFoldPayload,
} from '../../lib/api'
import EquityChart from './EquityChart'
import MonthlyHeatmap from './MonthlyHeatmap'

interface BacktestProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
  initialStrategyId?: string
  initialTaskId?: string
}

type Segment = 'all' | 'is' | 'oos'
type ResultTab = 'overview' | 'monthly' | 'walk-forward' | 'sensitivity' | 'trades' | 'overfit' | 'history'

const STRATEGIES = [
  { value: 'dual_ma', label: '双均线', shortLabel: 'MA', family: 'trend' },
  { value: 'momentum', label: '横截面动量', shortLabel: 'MOM', family: 'momentum' },
  { value: 'mean_reversion', label: '均值回归', shortLabel: 'REV', family: 'reversion' },
]

interface ConfigState {
  universe: string[]
  startDate: string
  endDate: string
  inSampleEndDate: string
  initialCash: number
  strategyName: string
  // dual_ma
  shortWindow: number
  longWindow: number
  targetGross: number
  maxPositions: number
  // momentum
  lookback: number
  skip: number
  // mean_reversion
  zThreshold: number
  maxPositionsMR: number
  targetGrossMR: number
  // cost
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
  maxPositions: 5,
  lookback: 20,
  skip: 1,
  zThreshold: 1.5,
  maxPositionsMR: 10,
  targetGrossMR: 0.90,
  commissionRate: 0.0003,
  minCommission: 5,
  stampTaxRate: 0.001,
  slippageBps: 1,
}

function buildPayload(config: ConfigState): BacktestCreatePayload {
  const strategyParams: Record<string, number> =
    config.strategyName === 'dual_ma'
      ? { short_window: config.shortWindow, long_window: config.longWindow, target_gross: config.targetGross, max_positions: config.maxPositions }
      : config.strategyName === 'momentum'
      ? { lookback: config.lookback, skip: config.skip, max_positions: config.maxPositions, target_gross: config.targetGross }
      : { lookback: config.lookback, z_threshold: config.zThreshold, max_positions: config.maxPositionsMR, target_gross: config.targetGrossMR }

  return {
    universe: config.universe,
    startDate: config.startDate,
    endDate: config.endDate,
    inSampleEndDate: config.inSampleEndDate || undefined,
    initialCash: config.initialCash,
    strategyName: config.strategyName,
    strategyParams,
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

function toneFor(v: number | null | undefined, kind: 'return' | 'sharpe' | 'dd' | 'calmar' | 'sortino' | 'vol' | 'pf' | 'neutral'): string {
  if (v == null) return 'gray'
  if (kind === 'dd') return v <= -0.20 ? 'red' : v <= -0.08 ? 'yellow' : 'green'
  if (kind === 'sharpe' || kind === 'sortino') return v >= 1.5 ? 'green' : v >= 0.8 ? 'blue' : v >= 0 ? 'yellow' : 'red'
  if (kind === 'calmar') return v >= 1.0 ? 'green' : v >= 0.5 ? 'blue' : v >= 0 ? 'yellow' : 'red'
  if (kind === 'vol') return v <= 0.12 ? 'green' : v <= 0.20 ? 'yellow' : 'red'
  if (kind === 'pf') return v >= 1.5 ? 'green' : v >= 1.0 ? 'blue' : 'red'
  if (kind === 'return') return v >= 0 ? 'green' : 'red'
  return 'blue'
}

// Maps strategy family to the closest builtin strategy engine name.
const FAMILY_TO_ENGINE: Record<string, string> = {
  trend: 'dual_ma',
  momentum: 'momentum',
  mean_reversion: 'mean_reversion',
  value: 'dual_ma',
  arbitrage: 'mean_reversion',
  'multi-factor': 'momentum',
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
  const [showParams, setShowParams] = useState(true)
  const [elapsed, setElapsed] = useState(0)

  // Strategy source: factory strategies vs. builtin engines
  const [strategySource, setStrategySource] = useState<'builtin' | 'factory'>('builtin')
  const [factoryStrategies, setFactoryStrategies] = useState<StrategyListItem[]>([])
  const [selectedFactoryId, setSelectedFactoryId] = useState<string | null>(null)

  // Universe builder mode: agent-recommended vs. manual chip-selection
  const [universeMode, setUniverseMode] = useState<'manual' | 'agent'>('manual')
  const [agentBuilding, setAgentBuilding] = useState(false)
  const [agentSuggestion, setAgentSuggestion] = useState<UniverseSuggestResult | null>(null)
  const [agentMinBars, setAgentMinBars] = useState(60)
  const [agentMaxSymbols, setAgentMaxSymbols] = useState(20)
  const resultPanelRef = useRef<HTMLElement | null>(null)

  const flash = (tone: 'green' | 'red' | 'blue', text: string, ms = 3500) => {
    setStatusMsg({ tone, text })
    setTimeout(() => setStatusMsg(null), ms)
  }

  const refreshHistory = useCallback(async () => {
    try { setHistory(await api.backtest.list(30)) } catch { /* ignore */ }
  }, [])

  const openHistory = useCallback(() => {
    setResultTab('history')
    window.requestAnimationFrame(() => {
      resultPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }, [])

  useEffect(() => {
    void api.data.symbols().then((rows) => {
      setSymbols(rows)
      if (rows.length && !config.startDate) {
        const cover = pickCoverage(rows)
        setConfig((prev) => ({
          ...prev,
          startDate: prev.startDate || cover.startDate,
          endDate: prev.endDate || cover.endDate,
        }))
      }
    })
    void api.strategy.backtestReady().then((res) => {
      setFactoryStrategies(res.items)
    }).catch(() => { /* no factory strategies yet */ })
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleFactoryStrategySelect = useCallback((id: string) => {
    setSelectedFactoryId(id)
    const s = factoryStrategies.find((f) => f.id === id)
    if (!s) return
    const engineName = FAMILY_TO_ENGINE[s.family.toLowerCase()] ?? 'dual_ma'
    setConfig((prev) => ({ ...prev, strategyName: engineName }))
    flash('blue', `已选择策略工厂策略「${s.name}」→ 使用 ${engineName} 引擎`)
  }, [factoryStrategies])

  const handleAgentBuild = useCallback(async () => {
    setAgentBuilding(true)
    try {
      const engineFamily = config.strategyName === 'momentum' ? 'momentum'
        : config.strategyName === 'mean_reversion' ? 'mean_reversion' : 'trend'
      const result = await api.backtest.suggestUniverse({
        strategyFamily: engineFamily,
        maxSymbols: agentMaxSymbols,
        minBars: agentMinBars,
        diversify: true,
      })
      setAgentSuggestion(result)
      setConfig((prev) => ({ ...prev, universe: result.symbols }))
      flash('green', `Agent 推荐了 ${result.symbols.length} 个标的（多样性 ${Math.round(result.diversityScore * 100)}%）`)
    } catch (e) {
      flash('red', `Agent 构建失败: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setAgentBuilding(false)
    }
  }, [config.strategyName, agentMaxSymbols, agentMinBars])

  useEffect(() => {
    if (!activeTaskId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setReport(null)
      return
    }
    void api.backtest.report(activeTaskId).then(setReport).catch((e) => {
      setStatusMsg({ tone: 'red', text: `加载报告失败: ${e instanceof Error ? e.message : String(e)}` })
    })
  }, [activeTaskId])

  useEffect(() => {
    if (initialStrategyId && !initialTaskId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatusMsg({ tone: 'blue', text: `已为策略 ${initialStrategyId.slice(0, 8)}… 准备配置，按"运行回测"开始。` })
    }
  }, [initialStrategyId, initialTaskId])

  useEffect(() => {
    if (running === null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setElapsed(0)
      return
    }
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [running])

  const validate = (): string | null => {
    if (!config.universe.length) return '请至少选择一个标的'
    if (!config.startDate || !config.endDate) return '请填写起止日期'
    if (config.startDate > config.endDate) return '起止日期顺序有误'
    if (config.inSampleEndDate && (config.inSampleEndDate < config.startDate || config.inSampleEndDate >= config.endDate)) {
      return 'IS 切分日必须在 [起始, 结束) 范围内'
    }
    return null
  }

  const runBacktest = async () => {
    const err = validate()
    if (err) { flash('red', err); return }
    setRunning('backtest'); setStatusMsg(null)
    try {
      const result = await api.backtest.runReal(buildPayload(config))
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `回测完成，task=${result.taskId.slice(0, 8)}…`)
      setResultTab('overview')
    } catch (e) { flash('red', `回测失败: ${e instanceof Error ? e.message : String(e)}`, 6000) }
    finally { setRunning(null) }
  }

  const runWalkForward = async () => {
    const err = validate()
    if (err) { flash('red', err); return }
    setRunning('walk-forward')
    try {
      const result = await api.backtest.walkForward({ ...buildPayload(config), folds: 4, trainRatio: 0.7 })
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `Walk-Forward 完成 (${result.folds.length} 折)`)
      setResultTab('walk-forward')
    } catch (e) { flash('red', `Walk-Forward 失败: ${e instanceof Error ? e.message : String(e)}`, 6000) }
    finally { setRunning(null) }
  }

  const runSensitivity = async () => {
    if (!activeTaskId) { flash('blue', '先运行一次回测，再做敏感性扫描'); return }
    const err = validate()
    if (err) { flash('red', err); return }
    setRunning('sensitivity')
    try {
      const result = await api.backtest.sensitivity(buildPayload(config))
      setActiveTaskId(result.taskId)
      await refreshHistory()
      flash('green', `敏感性扫描完成 (${result.runs.length} 变体)`)
      setResultTab('sensitivity')
    } catch (e) { flash('red', `敏感性扫描失败: ${e instanceof Error ? e.message : String(e)}`, 6000) }
    finally { setRunning(null) }
  }

  const toggleSymbol = (symbol: string) =>
    setConfig((prev) => ({
      ...prev,
      universe: prev.universe.includes(symbol) ? prev.universe.filter((s) => s !== symbol) : [...prev.universe, symbol],
    }))

  const loadHistory = (item: BacktestTaskListPayload) => {
    setActiveTaskId(item.taskId)
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

  const activeStrategy = STRATEGIES.find((s) => s.value === config.strategyName) ?? STRATEGIES[0]

  return (
    <div className="bt-workbench">
      {/* ── Header ─── */}
      <header className="bt-header">
        <div className="bt-header-left">
          <div className="bt-header-title-row">
            <span className={`status-dot-${running ? 'blue' : report ? 'green' : 'gray'}`} style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block', marginRight: 8, flexShrink: 0 }} />
            <h2 className="bt-title">回测实验室</h2>
            <span className="bt-strategy-badge">{activeStrategy.shortLabel}</span>
          </div>
          <span className="bt-subtitle">真实日线行情 · {activeStrategy.label} · IS/OOS · Walk-Forward · 敏感性 · 过拟合评估</span>
        </div>
        <div className="bt-actions">
          {running && (
            <span className="bt-running-timer">
              <span className="bt-spinner" />
              {running === 'backtest' ? '回测' : running === 'walk-forward' ? 'Walk-Forward' : '敏感性'}中… {elapsed}s
            </span>
          )}
          <button className={`bt-btn ${resultTab === 'history' ? 'bt-btn-on' : ''}`} onClick={openHistory}>
            运行历史 {history.length ? `(${history.length})` : ''}
          </button>
        </div>
      </header>

      {statusMsg && <div className={`bt-toast bt-toast-${statusMsg.tone}`}>{statusMsg.text}</div>}

      <div className="bt-layout">
        {/* ── Top: Experiment Command Center ── */}
        <section className="bt-config">

          {/* Strategy selector */}
          <div className="bt-config-section">
            <div className="bt-label-row">
              <label className="bt-label">策略来源</label>
              <div className="bt-source-toggle">
                <button
                  className={`bt-source-btn ${strategySource === 'builtin' ? 'on' : ''}`}
                  onClick={() => setStrategySource('builtin')}
                >内置策略</button>
                <button
                  className={`bt-source-btn ${strategySource === 'factory' ? 'on' : ''}`}
                  onClick={() => setStrategySource('factory')}
                >
                  策略工厂
                  {factoryStrategies.length > 0 && (
                    <span className="bt-source-count">{factoryStrategies.length}</span>
                  )}
                </button>
              </div>
            </div>

            {strategySource === 'builtin' && (
              <div className="bt-strategy-tabs">
                {STRATEGIES.map((s) => (
                  <button
                    key={s.value}
                    className={`bt-strategy-tab ${config.strategyName === s.value ? 'on' : ''}`}
                    onClick={() => { setConfig((p) => ({ ...p, strategyName: s.value })); setSelectedFactoryId(null) }}
                  >
                    <span className="bt-strategy-tab-short">{s.shortLabel}</span>
                    <span className="bt-strategy-tab-label">{s.label}</span>
                  </button>
                ))}
              </div>
            )}

            {strategySource === 'factory' && (
              <div className="bt-factory-selector">
                {factoryStrategies.length === 0 ? (
                  <div className="bt-factory-empty">
                    策略工厂中暂无已审核策略。
                    <br />
                    <span className="bt-factory-hint">在「策略工厂」中将策略推进到「研究」阶段后，即可在此处选择。</span>
                  </div>
                ) : (
                  <>
                    <select
                      className="bt-input bt-factory-select"
                      value={selectedFactoryId ?? ''}
                      onChange={(e) => handleFactoryStrategySelect(e.target.value)}
                    >
                      <option value="">— 选择策略工厂策略 —</option>
                      {factoryStrategies.map((s) => (
                        <option key={s.id} value={s.id}>
                          [{s.status}] {s.name} · {s.family} · SR {s.sharpe?.toFixed(2) ?? '—'}
                        </option>
                      ))}
                    </select>
                    {selectedFactoryId && (
                      <div className="bt-factory-meta">
                        {(() => {
                          const s = factoryStrategies.find((f) => f.id === selectedFactoryId)
                          if (!s) return null
                          const engine = FAMILY_TO_ENGINE[s.family.toLowerCase()] ?? 'dual_ma'
                          return (
                            <>
                              <span className="bt-factory-tag">{s.family}</span>
                              <span className="bt-factory-tag">{s.market}</span>
                              <span className="bt-factory-engine">引擎: {engine}</span>
                              {s.annualReturn != null && (
                                <span className={`bt-factory-stat ${s.annualReturn >= 0 ? 'pos' : 'neg'}`}>
                                  CAGR {s.annualReturn >= 0 ? '+' : ''}{(s.annualReturn * 100).toFixed(1)}%
                                </span>
                              )}
                            </>
                          )
                        })()}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Universe */}
          <div className={`bt-config-section bt-universe-section ${universeMode === 'agent' ? 'agent-mode' : ''}`}>
            <div className="bt-label-row">
              <label className="bt-label">
                股票池 <span className="bt-label-count">({config.universe.length})</span>
              </label>
              <div className="bt-source-toggle">
                <button
                  className={`bt-source-btn ${universeMode === 'manual' ? 'on' : ''}`}
                  onClick={() => setUniverseMode('manual')}
                >手动</button>
                <button
                  className={`bt-source-btn ${universeMode === 'agent' ? 'on' : ''}`}
                  onClick={() => setUniverseMode('agent')}
                >Agent 构建</button>
              </div>
            </div>

            {universeMode === 'agent' && (
              <div className="bt-agent-builder">
                <div className="bt-agent-criteria">
                  <label className="bt-field">
                    <span>最少 K 线</span>
                    <input
                      type="number"
                      className="bt-input small"
                      value={agentMinBars}
                      min={20}
                      max={500}
                      step={20}
                      onChange={(e) => setAgentMinBars(Number(e.target.value))}
                    />
                  </label>
                  <label className="bt-field">
                    <span>最大标的数</span>
                    <input
                      type="number"
                      className="bt-input small"
                      value={agentMaxSymbols}
                      min={5}
                      max={100}
                      step={5}
                      onChange={(e) => setAgentMaxSymbols(Number(e.target.value))}
                    />
                  </label>
                  <button
                    className="bt-btn bt-btn-agent"
                    disabled={agentBuilding}
                    onClick={() => void handleAgentBuild()}
                  >
                    {agentBuilding ? <><span className="bt-spinner" /> 生成中…</> : '⊕ 生成推荐'}
                  </button>
                </div>

                {agentSuggestion && (
                  <div className="bt-agent-result">
                    {/* Summary header */}
                    <div className="bt-agent-summary-row">
                      <div className="bt-agent-stats">
                        <span className="bt-agent-stat">
                          <span className="bt-agent-stat-label">推荐入选</span>
                          <span className="bt-agent-stat-value">{agentSuggestion.symbols.length}</span>
                        </span>
                        <span className="bt-agent-stat">
                          <span className="bt-agent-stat-label">当前已选</span>
                          <span className={`bt-agent-stat-value ${config.universe.length !== agentSuggestion.symbols.length ? 'mid' : 'pos'}`}>
                            {config.universe.length}
                          </span>
                        </span>
                        <span className="bt-agent-stat">
                          <span className="bt-agent-stat-label">全部候选</span>
                          <span className="bt-agent-stat-value">{agentSuggestion.candidates.length}</span>
                        </span>
                        <span className="bt-agent-stat">
                          <span className="bt-agent-stat-label">覆盖度</span>
                          <span className={`bt-agent-stat-value ${agentSuggestion.diversityScore >= 0.6 ? 'pos' : agentSuggestion.diversityScore >= 0.3 ? 'mid' : 'neg'}`}>
                            {Math.round(agentSuggestion.diversityScore * 100)}%
                          </span>
                        </span>
                        <span className="bt-agent-stat">
                          <span className="bt-agent-stat-label">时间跨度</span>
                          <span className="bt-agent-stat-value">{agentSuggestion.coverageDays}d</span>
                        </span>
                      </div>
                      <div className="bt-agent-rec">{agentSuggestion.recommendation}</div>
                    </div>

                    {/* AI model attribution */}
                    {agentSuggestion.aiModel && (
                      <div className="bt-agent-model-tag">
                        <span className="bt-agent-model-name">AI: {agentSuggestion.aiModel}</span>
                        <span className="bt-agent-model-notice">每个标的的选择/排除理由均由 AI 生成，交易员可自由修改，修改记入溯源</span>
                      </div>
                    )}

                    {/* Full candidate table — symbol + data stats + AI reason, all visible */}
                    <div className="bt-agent-candidate-header">
                      <span className="bt-agent-candidate-label">
                        逐标的明细
                        <span className="bt-agent-candidate-hint">·  点击行切换入选 / 排除</span>
                      </span>
                      <div className="bt-agent-bulk-actions">
                        <button className="bt-chip-btn" onClick={() => setConfig((p) => ({ ...p, universe: agentSuggestion.symbols }))}>恢复推荐</button>
                        <button className="bt-chip-btn" onClick={() => setConfig((p) => ({ ...p, universe: agentSuggestion.candidates.map((c) => c.symbol) }))}>全选</button>
                        <button className="bt-chip-btn" onClick={() => setConfig((p) => ({ ...p, universe: [] }))}>清空</button>
                      </div>
                    </div>
                    <div className="bt-agent-table">
                      <div className="bt-agent-table-head">
                        <span className="bt-ath-status" />
                        <span className="bt-ath-symbol">代码</span>
                        <span className="bt-ath-name">名称</span>
                        <span className="bt-ath-bars">K线</span>
                        <span className="bt-ath-range">数据区间</span>
                        <span className="bt-ath-days">覆盖</span>
                        <span className="bt-ath-reason">AI 选择理由</span>
                      </div>
                      {agentSuggestion.candidates.map((c) => {
                        const isSelected = config.universe.includes(c.symbol)
                        const wasRecommended = agentSuggestion.symbols.includes(c.symbol)
                        const stateClass = isSelected ? 'on' : wasRecommended ? 'deselected' : 'off'
                        return (
                          <div
                            key={c.symbol}
                            className={`bt-agent-table-row ${stateClass}`}
                            onClick={() => toggleSymbol(c.symbol)}
                          >
                            <span className={`bt-atr-status ${stateClass}`}>
                              {isSelected ? '✓' : wasRecommended ? '✕' : '○'}
                            </span>
                            <span className="bt-atr-symbol">{c.symbol}</span>
                            <span className="bt-atr-name">{c.name ?? '—'}</span>
                            <span className="bt-atr-bars">{c.bars}</span>
                            <span className="bt-atr-range">{c.startDate.slice(0, 7)} ~ {c.endDate.slice(0, 7)}</span>
                            <span className="bt-atr-days">{c.coverageDays}d</span>
                            <span className="bt-atr-reason">
                              {c.reason ?? <span className="bt-atr-no-reason">—</span>}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    {config.universe.length !== agentSuggestion.symbols.length && (
                      <div className="bt-agent-diff-note">
                        已偏离 Agent 推荐（推荐 {agentSuggestion.symbols.length} 个，当前 {config.universe.length} 个）。
                        修改将记入回测溯源，确保可审计。
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {universeMode === 'manual' && (
              <>
                <div className="bt-chip-actions" style={{ marginBottom: 6 }}>
                  <button className="bt-chip-btn" onClick={() => setConfig((p) => ({ ...p, universe: symbols.map((s) => s.symbol) }))}>全选</button>
                  <button className="bt-chip-btn" onClick={() => setConfig((p) => ({ ...p, universe: [] }))}>清空</button>
                  <span className="bt-overfit-warn">
                    ⚠ 固定股票池存在回测过拟合风险，建议使用 Agent 构建
                  </span>
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
              </>
            )}
          </div>

          {/* Date range */}
          <div className="bt-config-section">
            <label className="bt-label">回测区间</label>
            <div className="bt-row">
              <input type="date" className="bt-input" value={config.startDate} onChange={(e) => setConfig({ ...config, startDate: e.target.value })} />
              <span className="bt-row-sep">→</span>
              <input type="date" className="bt-input" value={config.endDate} onChange={(e) => setConfig({ ...config, endDate: e.target.value })} />
            </div>
          </div>

          {/* IS split */}
          <div className="bt-config-section">
            <label className="bt-label">IS 切分 <span className="bt-label-opt">（可选）</span></label>
            <input
              type="date"
              className="bt-input"
              value={config.inSampleEndDate}
              onChange={(e) => setConfig({ ...config, inSampleEndDate: e.target.value })}
            />
            <div className="bt-hint">切分日之前为样本内（IS），之后为样本外（OOS）</div>
          </div>

          {/* Initial cash */}
          <div className="bt-config-section">
            <label className="bt-label">初始资金（元）</label>
            <input
              type="number"
              className="bt-input"
              value={config.initialCash}
              min={1000}
              step={100000}
              onChange={(e) => setConfig({ ...config, initialCash: Number(e.target.value) })}
            />
          </div>

          {/* Strategy params */}
          <div className="bt-config-section">
            <button className="bt-collapse" onClick={() => setShowParams((v) => !v)}>
              {showParams ? '▼' : '▸'} 策略参数
            </button>
            {showParams && (
              <div className="bt-params">
                {config.strategyName === 'dual_ma' && (
                  <>
                    <div className="bt-row">
                      <NumberField label="短均线" value={config.shortWindow} onChange={(v) => setConfig({ ...config, shortWindow: v })} step={1} min={2} />
                      <NumberField label="长均线" value={config.longWindow} onChange={(v) => setConfig({ ...config, longWindow: v })} step={1} min={3} />
                    </div>
                    <div className="bt-row">
                      <NumberField label="目标毛敞口" value={config.targetGross} onChange={(v) => setConfig({ ...config, targetGross: v })} step={0.05} min={0.1} max={1.0} />
                      <NumberField label="最大持仓" value={config.maxPositions} onChange={(v) => setConfig({ ...config, maxPositions: v })} step={1} min={1} />
                    </div>
                  </>
                )}
                {config.strategyName === 'momentum' && (
                  <>
                    <div className="bt-row">
                      <NumberField label="回看窗口" value={config.lookback} onChange={(v) => setConfig({ ...config, lookback: v })} step={5} min={5} />
                      <NumberField label="跳过天数" value={config.skip} onChange={(v) => setConfig({ ...config, skip: v })} step={1} min={0} />
                    </div>
                    <div className="bt-row">
                      <NumberField label="最大持仓" value={config.maxPositions} onChange={(v) => setConfig({ ...config, maxPositions: v })} step={1} min={1} />
                      <NumberField label="目标毛敞口" value={config.targetGross} onChange={(v) => setConfig({ ...config, targetGross: v })} step={0.05} min={0.1} max={1.0} />
                    </div>
                  </>
                )}
                {config.strategyName === 'mean_reversion' && (
                  <>
                    <div className="bt-row">
                      <NumberField label="回看窗口" value={config.lookback} onChange={(v) => setConfig({ ...config, lookback: v })} step={5} min={5} />
                      <NumberField label="Z-score 阈值" value={config.zThreshold} onChange={(v) => setConfig({ ...config, zThreshold: v })} step={0.25} min={0.5} max={4.0} />
                    </div>
                    <div className="bt-row">
                      <NumberField label="最大持仓" value={config.maxPositionsMR} onChange={(v) => setConfig({ ...config, maxPositionsMR: v })} step={1} min={1} />
                      <NumberField label="目标毛敞口" value={config.targetGrossMR} onChange={(v) => setConfig({ ...config, targetGrossMR: v })} step={0.05} min={0.1} max={1.0} />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Cost config */}
          <div className="bt-config-section">
            <button className="bt-collapse" onClick={() => setShowCost((v) => !v)}>
              {showCost ? '▼' : '▸'} 成本假设
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
          <div className="bt-run-panel">
            <div>
              <span className="bt-label">实验执行</span>
              <div className="bt-run-summary">
                {config.universe.length} 标的 · {config.startDate || '?'} → {config.endDate || '?'}
              </div>
            </div>
            <div className="bt-run-actions">
              <button className="bt-btn bt-btn-primary" disabled={running !== null} onClick={() => void runBacktest()}>
                {running === 'backtest' ? '运行中…' : '▶ 运行回测'}
              </button>
              <button className="bt-btn" disabled={running !== null} onClick={() => void runWalkForward()}>
                {running === 'walk-forward' ? '运行中…' : 'Walk-Forward'}
              </button>
              <button className="bt-btn" disabled={running !== null} onClick={() => void runSensitivity()}>
                {running === 'sensitivity' ? '运行中…' : '敏感性扫描'}
              </button>
            </div>
          </div>
        </section>

        {/* ── Results ── */}
        <main className="bt-result" ref={resultPanelRef}>
          <LabTabs
            report={report}
            resultTab={resultTab}
            setResultTab={setResultTab}
            historyCount={history.length}
            onOpenHistory={openHistory}
          />
          {resultTab === 'history' ? (
            <HistoryView
              history={history}
              activeTaskId={activeTaskId}
              onRefresh={refreshHistory}
              onPick={(item) => {
                loadHistory(item)
                setResultTab('overview')
              }}
            />
          ) : !report ? (
            <div className="bt-result-empty">
              <div className="bt-empty-icon">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                  <rect x="6" y="32" width="8" height="10" rx="1" fill="rgba(66,232,255,0.25)" />
                  <rect x="18" y="22" width="8" height="20" rx="1" fill="rgba(66,232,255,0.45)" />
                  <rect x="30" y="14" width="8" height="28" rx="1" fill="rgba(79,240,162,0.5)" />
                  <path d="M8 28 L20 20 L32 10" stroke="#42e8ff" strokeWidth="2" strokeLinecap="round" />
                  <circle cx="32" cy="10" r="2.5" fill="#4ff0a2" />
                </svg>
              </div>
              <div className="bt-empty-title">配置策略，运行回测</div>
              <div className="bt-empty-desc">选择策略、股票池与日期范围后点击"▶ 运行回测"，或从右侧历史列表中选取一次已完成的回测</div>
            </div>
          ) : (
            <ResultView
              report={report}
              segment={segment}
              segmentMetric={segmentMetric}
              setSegment={setSegment}
              resultTab={resultTab}
            />
          )}
        </main>
      </div>
    </div>
  )
}

// ── HistoryItem ──────────────────────────────────────────────────────────────

function HistoryItem({ item: h, active, onClick }: { item: BacktestTaskListPayload; active: boolean; onClick: () => void }) {
  const ret = h.cumulativeReturn
  const strategy = STRATEGIES.find((s) => s.value === h.strategyName) ?? { shortLabel: h.strategyName ?? 'MA', family: 'trend' }
  return (
    <button className={`bt-history-item ${active ? 'on' : ''}`} onClick={onClick}>
      <div className="bt-history-row1">
        <span className="bt-history-name">{h.strategyName ?? 'dual_ma'}</span>
        <span className={`bt-history-status status-tag-${h.status === 'completed' ? 'green' : 'yellow'}`}>{h.status}</span>
      </div>
      <div className="bt-history-row2">{h.startDate ?? '?'} → {h.endDate ?? '?'}</div>
      <div className="bt-history-row3">
        <span className={ret != null && ret >= 0 ? 'mini pos' : 'mini neg'}>{pct(ret, 1)}</span>
        <span className="mini">SR {num(h.sharpeRatio)}</span>
        <span className="mini neg">{pct(h.maxDrawdown, 1)}</span>
        {h.overfitLevel && <span className={`mini overfit-${h.overfitLevel}`}>{h.overfitLevel}</span>}
      </div>
      <div className="bt-history-meta">
        <span className="bt-history-family">{strategy.shortLabel}</span>
        {h.universe.length > 0 && <span className="bt-history-universe">{h.universe.length} 标的</span>}
      </div>
    </button>
  )
}

function HistoryView({
  history,
  activeTaskId,
  onRefresh,
  onPick,
}: {
  history: BacktestTaskListPayload[]
  activeTaskId: string | null
  onRefresh: () => Promise<void>
  onPick: (item: BacktestTaskListPayload) => void
}) {
  return (
    <div className="bt-history-page">
      <div className="bt-history-page-head">
        <div>
          <span className="bt-summary-label">实验记录</span>
          <h3>运行历史</h3>
        </div>
        <button className="bt-btn" onClick={() => void onRefresh()}>↺ 刷新</button>
      </div>
      <div className="bt-history-page-list">
        {history.length === 0 ? (
          <div className="bt-empty-line">尚无历史回测</div>
        ) : (
          history.map((h) => (
            <HistoryItem key={h.taskId} item={h} active={h.taskId === activeTaskId} onClick={() => onPick(h)} />
          ))
        )}
      </div>
    </div>
  )
}

function LabTabs({
  report,
  resultTab,
  setResultTab,
  historyCount,
  onOpenHistory,
}: {
  report: BacktestReportPayload | null
  resultTab: ResultTab
  setResultTab: (t: ResultTab) => void
  historyCount: number
  onOpenHistory: () => void
}) {
  const monthlyReturns = report?.summary.monthlyReturns ?? {}
  const monthCount = Object.keys(monthlyReturns).length
  const tabs: [ResultTab, string, boolean][] = [
    ['overview', '总览', Boolean(report)],
    ['monthly', `月度${monthCount ? ` (${monthCount}M)` : ''}`, Boolean(report)],
    ['walk-forward', `Walk-Forward${report?.walkForwardFolds.length ? ` (${report.walkForwardFolds.length})` : ''}`, Boolean(report)],
    ['sensitivity', `敏感性${report?.sensitivityRuns.length ? ` (${report.sensitivityRuns.length})` : ''}`, Boolean(report)],
    ['trades', `成交${report?.trades.length ? ` (${report.trades.length})` : ''}`, Boolean(report)],
    ['overfit', '过拟合', Boolean(report)],
    ['history', `运行历史${historyCount ? ` (${historyCount})` : ''}`, true],
  ]
  return (
    <div className="bt-tabs bt-tabs-sticky">
      {tabs.map(([tab, label, enabled]) => (
        <button
          key={tab}
          className={`bt-tab ${resultTab === tab ? 'on' : ''}`}
          disabled={!enabled}
          onClick={() => {
            if (!enabled) return
            if (tab === 'history') onOpenHistory()
            else setResultTab(tab)
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

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
      <input type="number" className="bt-input small" value={value} step={step} min={min} max={max} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}

// ── ResultView ───────────────────────────────────────────────────────────────

interface ResultViewProps {
  report: BacktestReportPayload
  segment: Segment
  segmentMetric: BacktestMetricPayload | null
  setSegment: (s: Segment) => void
  resultTab: ResultTab
}

function ResultView({ report, segment, segmentMetric, setSegment, resultTab }: ResultViewProps) {
  const hasSplit = Boolean(report.summary.inSampleEndDate && report.summary.inSampleMetrics)
  const monthlyReturns = report.summary.monthlyReturns ?? {}

  return (
    <>
      <div className="bt-summary-head">
        <div className="bt-summary-id-row">
          <span className="bt-summary-label">任务</span>
          <code className="bt-summary-id">{report.taskId.slice(0, 12)}…</code>
          {report.summary.runId && <span className="bt-summary-run">run {report.summary.runId.slice(0, 8)}</span>}
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

      <div className="bt-tab-body">
        {resultTab === 'overview' && <OverviewView report={report} />}
        {resultTab === 'monthly' && <MonthlyHeatmap monthlyReturns={monthlyReturns} />}
        {resultTab === 'walk-forward' && <WalkForwardView folds={report.walkForwardFolds} />}
        {resultTab === 'sensitivity' && <SensitivityView runs={report.sensitivityRuns} />}
        {resultTab === 'trades' && <TradesView trades={report.trades} />}
        {resultTab === 'overfit' && <OverfitView overfit={report.overfit} />}
      </div>
    </>
  )
}

function OverviewView({ report }: { report: BacktestReportPayload }) {
  return (
    <div className="bt-overview">
      <PromotionGateView report={report} />
      <EquityChart equity={report.summary.equityCurve} inSampleEndDate={report.summary.inSampleEndDate} />
    </div>
  )
}

function PromotionGateView({ report }: { report: BacktestReportPayload }) {
  const gate = report.promotionGate
  const checklist = report.labChecklist ?? []
  if (!gate && !checklist.length) return null
  return (
    <section className={`bt-gate bt-gate-${gate?.decision ?? 'review'}`}>
      <div className="bt-gate-main">
        <span className="bt-gate-label">实验门禁</span>
        <div className="bt-gate-title">{gate?.label ?? '研究复核'}</div>
        <div className="bt-gate-score">{gate?.readinessScore ?? 0}</div>
      </div>
      <div className="bt-check-grid">
        {checklist.map((item) => (
          <div key={item.id} className={`bt-check bt-check-${item.status}`} title={item.detail}>
            <span className="bt-check-status">{item.status === 'pass' ? '✓' : item.status === 'warn' ? '!' : '✗'}</span>
            <span className="bt-check-label">{item.label}</span>
          </div>
        ))}
      </div>
      {gate?.nextActions.length ? (
        <div className="bt-next-actions">{gate.nextActions.map((a) => <span key={a}>{a}</span>)}</div>
      ) : null}
    </section>
  )
}

function MetricsStrip({ metric }: { metric: BacktestMetricPayload | null }) {
  if (!metric) return <div className="bt-metrics-empty">无可用指标</div>

  const row1 = [
    { label: '累计收益', value: pct(metric.cumulativeReturn), tone: toneFor(metric.cumulativeReturn, 'return') },
    { label: '年化收益', value: pct(metric.annualReturn), tone: toneFor(metric.annualReturn, 'return') },
    { label: '最大回撤', value: pct(metric.maxDrawdown), tone: toneFor(metric.maxDrawdown, 'dd') },
    { label: 'Sharpe', value: num(metric.sharpeRatio), tone: toneFor(metric.sharpeRatio, 'sharpe') },
    { label: '胜率', value: pct(metric.winRate, 1), tone: 'blue' },
  ]
  const row2 = [
    { label: 'Sortino', value: num(metric.sortinoRatio ?? 0), tone: toneFor(metric.sortinoRatio ?? 0, 'sortino') },
    { label: 'Calmar', value: num(metric.calmarRatio ?? 0), tone: toneFor(metric.calmarRatio ?? 0, 'calmar') },
    { label: '年化波动', value: pct(metric.volatility ?? 0, 1), tone: toneFor(metric.volatility ?? 0, 'vol') },
    { label: '盈亏比', value: num(metric.profitFactor ?? 0), tone: toneFor(metric.profitFactor ?? 0, 'pf') },
    { label: '换手率', value: num(metric.turnover), tone: 'blue' },
  ]

  return (
    <div className="bt-metrics-block">
      <div className="bt-metrics-strip">
        {row1.map((m) => (
          <div key={m.label} className={`bt-metric tone-${m.tone}`}>
            <span className="bt-metric-label">{m.label}</span>
            <span className="bt-metric-value">{m.value}</span>
          </div>
        ))}
      </div>
      <div className="bt-metrics-strip bt-metrics-strip-2">
        {row2.map((m) => (
          <div key={m.label} className={`bt-metric bt-metric-sm tone-${m.tone}`}>
            <span className="bt-metric-label">{m.label}</span>
            <span className="bt-metric-value">{m.value}</span>
          </div>
        ))}
      </div>
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
          <th>折</th><th>训练区间</th><th>训练收益</th><th>训练 SR</th><th>测试区间</th><th>测试收益</th><th>测试 SR</th><th>测试回撤</th>
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
          <tr><th>变体</th><th>累计收益</th><th>Sharpe</th><th>最大回撤</th><th>胜率</th></tr>
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
  const [symbolFilter, setSymbolFilter] = useState('')
  const [sideFilter, setSideFilter] = useState<'all' | 'buy' | 'sell'>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [pageSize, setPageSize] = useState(50)
  const [page, setPage] = useState(1)

  const symbols = useMemo(() => Array.from(new Set(trades.map((t) => t.symbol))).sort(), [trades])
  const filteredTrades = useMemo(() => {
    return trades.filter((t) => {
      if (symbolFilter && t.symbol !== symbolFilter) return false
      if (sideFilter !== 'all' && t.side !== sideFilter) return false
      if (startDate && t.tradeDate < startDate) return false
      if (endDate && t.tradeDate > endDate) return false
      return true
    })
  }, [trades, symbolFilter, sideFilter, startDate, endDate])

  const pageCount = Math.max(1, Math.ceil(filteredTrades.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageTrades = filteredTrades.slice((safePage - 1) * pageSize, safePage * pageSize)

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPage(1)
  }, [symbolFilter, sideFilter, startDate, endDate, pageSize])

  if (!trades.length) return <div className="bt-empty-line">本任务没有成交。</div>
  return (
    <div className="bt-table-workbench">
      <div className="bt-table-toolbar">
        <div className="bt-table-toolbar-main">
          <label className="bt-filter-field">
            <span>日期起</span>
            <input type="date" className="bt-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label className="bt-filter-field">
            <span>日期止</span>
            <input type="date" className="bt-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          <label className="bt-filter-field">
            <span>标的</span>
            <select className="bt-input" value={symbolFilter} onChange={(e) => setSymbolFilter(e.target.value)}>
              <option value="">全部</option>
              {symbols.map((symbol) => <option key={symbol} value={symbol}>{symbol}</option>)}
            </select>
          </label>
          <label className="bt-filter-field">
            <span>方向</span>
            <select className="bt-input" value={sideFilter} onChange={(e) => setSideFilter(e.target.value as 'all' | 'buy' | 'sell')}>
              <option value="all">全部</option>
              <option value="buy">BUY</option>
              <option value="sell">SELL</option>
            </select>
          </label>
        </div>
        <div className="bt-table-toolbar-side">
          <span>{filteredTrades.length} / {trades.length} 笔</span>
          <button className="bt-chip-btn" onClick={() => { setStartDate(''); setEndDate(''); setSymbolFilter(''); setSideFilter('all') }}>清空过滤</button>
        </div>
      </div>
      <div className="bt-table-scroll">
        <table className="bt-table bt-trades-table">
          <thead>
            <tr><th>日期</th><th>标的</th><th>方向</th><th>数量</th><th>价格</th><th>金额</th><th>目标权重</th><th>触发原因</th></tr>
          </thead>
          <tbody>
            {pageTrades.map((t, i) => (
              <tr key={`${t.tradeDate}-${t.symbol}-${i}`}>
                <td className="bt-date">{t.tradeDate}</td>
                <td>{t.symbol}</td>
                <td className={t.side === 'buy' ? 'pos' : 'neg'}>{t.side.toUpperCase()}</td>
                <td>{num(t.quantity, 0)}</td>
                <td>{num(t.price, 4)}</td>
                <td>{num(t.amount, 0)}</td>
                <td>{pct(t.targetWeight)}</td>
                <td className="bt-trade-reason">{t.reason ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!pageTrades.length && <div className="bt-empty-line">当前过滤条件下没有成交。</div>}
      </div>
      <div className="bt-pagination">
        <label className="bt-page-size">
          每页
          <select className="bt-input" value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </label>
        <div className="bt-page-actions">
          <button className="bt-chip-btn" disabled={safePage <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>上一页</button>
          <span>{safePage} / {pageCount}</span>
          <button className="bt-chip-btn" disabled={safePage >= pageCount} onClick={() => setPage((p) => Math.min(pageCount, p + 1))}>下一页</button>
        </div>
      </div>
    </div>
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
          <tr><th>组件</th><th>分数</th><th>详情</th></tr>
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
