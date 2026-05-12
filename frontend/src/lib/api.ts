import { mock } from '../data'
import type { MockData } from '../data/types'

const API_PREFIX = '/api/v1'

async function getJson<T>(path: string, fallback: () => T): Promise<T> {
  try {
    const res = await fetch(`${API_PREFIX}${path}`, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } catch {
    return fallback()
  }
}

async function postJson<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

async function putJson<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'PUT',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

async function deleteJson(path: string): Promise<void> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
}

export interface StrategyDetail {
  id: string
  name: string
  family: string
  description: string | null
  riskProfile: string
  market: string
  universe: string | null
  frequency: string
  status: string
  annualReturn: number | null
  maxDd: number | null
  sharpe: number | null
  oosScore: number | null
  createdAt: string
  updatedAt: string
  ownerId?: string | null
  versions: {
    id: string
    version: string
    codeText: string | null
    paramsSchema: string | null
    riskRules: string | null
    createdAt: string
  }[]
  recentEvents: { id: string; stage: string; event: string; progress: number; createdAt: string }[]
}

export interface StrategyUpdatePayload {
  name?: string
  family?: string
  description?: string | null
  riskProfile?: string
  market?: string
  universe?: string | null
  frequency?: string
  status?: string
}

// ── Phase 3 real-backtest types ──────────────────────────────────────────

export interface BacktestMetricPayload {
  cumulativeReturn: number
  annualReturn: number
  maxDrawdown: number
  sharpeRatio: number
  winRate: number
  turnover: number
}

export interface BacktestEquityPointPayload {
  tradeDate: string
  value: number
  drawdown: number | null
  phase: 'is' | 'oos'
}

export interface BacktestTaskResult {
  taskId: string
  runId: string | null
  status: string
  metrics: BacktestMetricPayload | null
  inSampleMetrics: BacktestMetricPayload | null
  outSampleMetrics: BacktestMetricPayload | null
  inSampleEndDate: string | null
  equityCurve: BacktestEquityPointPayload[]
}

export interface WalkForwardFoldPayload {
  foldIndex: number
  trainStart: string
  trainEnd: string
  testStart: string
  testEnd: string
  trainReturn: number
  testReturn: number
  trainSharpe: number
  testSharpe: number
  trainMaxDd: number
  testMaxDd: number
}

export interface SensitivityRunPayload {
  kind: 'param' | 'slippage'
  label: string
  isBaseline: boolean
  cumulativeReturn: number
  annualReturn: number
  maxDrawdown: number
  sharpeRatio: number
  winRate: number
  turnover: number
}

export interface OverfitComponentPayload {
  name: string
  score: number
  detail: string
}

export interface OverfitAssessmentPayload {
  score: number
  level: 'low' | 'medium' | 'high'
  components: OverfitComponentPayload[]
}

export interface BacktestTradePayload {
  tradeDate: string
  symbol: string
  side: string
  quantity: number
  price: number
  amount: number
  targetWeight: number
  totalCost: number
  netCashFlow: number
  reason: string | null
}

export interface BacktestTaskListPayload {
  taskId: string
  runId: string | null
  status: string
  strategyVersionId: string | null
  strategyName: string | null
  startDate: string | null
  endDate: string | null
  inSampleEndDate: string | null
  universe: string[]
  cumulativeReturn: number | null
  sharpeRatio: number | null
  maxDrawdown: number | null
  overfitLevel: string | null
  createdAt: string
}

export interface SymbolSummary {
  symbol: string
  bars: number
  startDate: string
  endDate: string
}

export interface BacktestReportPayload {
  taskId: string
  runId: string | null
  summary: BacktestTaskResult
  walkForwardFolds: WalkForwardFoldPayload[]
  sensitivityRuns: SensitivityRunPayload[]
  overfit: OverfitAssessmentPayload | null
  trades: BacktestTradePayload[]
  featureUsage: { featureId: string; featureName: string; featureVersion: string; role: string | null }[]
  lineageNodeCount: number
  lineageEdgeCount: number
}

export interface BacktestCreatePayload {
  universe: string[]
  startDate: string
  endDate: string
  strategyName?: string
  initialCash?: number
  inSampleEndDate?: string
  strategyParams?: Record<string, unknown>
  costConfig?: {
    commissionRate?: number
    minCommission?: number
    stampTaxRate?: number
    slippageBps?: number
  }
}

export interface WalkForwardCreatePayload extends BacktestCreatePayload {
  folds?: number
  trainRatio?: number
}

// ── Phase 4 paper-trading types ──────────────────────────────────────────

export interface PaperAccount {
  id: string
  name: string
  ownerId: string
  strategyId: string | null
  strategyVersionId: string | null
  market: string
  baseCurrency: string
  initialCash: number
  cash: number
  inceptionDate: string | null
  lastProcessedDate: string | null
  peakNav: number | null
  status: string
}

export interface PaperAccountCreatePayload {
  name: string
  ownerId?: string
  strategyId?: string
  strategyVersionId?: string
  market?: string
  baseCurrency?: string
  initialCash?: number
  inceptionDate?: string
  costConfig?: {
    commission_rate?: number
    min_commission?: number
    stamp_tax_rate?: number
    slippage_bps?: number
  }
}

export interface PaperPosition {
  symbol: string
  quantity: number
  avgCost: number
  lastPrice: number | null
  marketValue: number
  weight: number
}

export interface PaperOrder {
  id: string
  accountId: string
  strategyId: string | null
  tradeDate: string
  symbol: string
  side: string
  targetWeight: number
  targetQuantity: number
  filledQuantity: number
  status: string
  reason: string | null
  rejectionReason: string | null
}

export interface PaperFill {
  id: string
  orderId: string
  tradeDate: string
  symbol: string
  side: string
  quantity: number
  price: number
  amount: number
  commission: number
  stampTax: number
  slippage: number
  totalCost: number
}

export interface PaperNavPoint {
  tradeDate: string
  nav: number
  cash: number
  marketValue: number
  dailyReturn: number | null
  drawdown: number | null
}

export interface PaperRiskBreach {
  id: string
  tradeDate: string
  rule: string
  severity: string
  detail: string | null
  status: string
}

export interface RunEodSummary {
  accountId: string
  tradeDate: string
  ordersCreated: number
  ordersFilled: number
  ordersRejected: number
  breaches: number
  nav: number | null
}

type DashboardOverview = MockData['dashboard']

export const api = {
  dashboard: {
    overview: () =>
      getJson<DashboardOverview>('/dashboard/overview', () => mock.dashboard),
  },
  strategy: {
    overview: () => getJson<MockData['strategy']>('/strategies/overview', () => mock.strategy),
    createTask: (payload: { prompt: string; market: string; riskProfile: string }) =>
      postJson<{
        id: string
        status: string
        progress: number
        stage?: string
      }>('/strategies/tasks', payload),
    getTask: (taskId: string) =>
      getJson<{
        id: string
        status: string
        progress: number
        stage: string | null
        strategyId: string | null
        backtestTaskId: string | null
        backtestRunId: string | null
        error: string | null
      }>(`/strategies/tasks/${encodeURIComponent(taskId)}`, () => ({
        id: taskId,
        status: 'failed',
        progress: 100,
        stage: 'failed',
        strategyId: null,
        backtestTaskId: null,
        backtestRunId: null,
        error: 'Strategy task API unavailable',
      })),
    getFeed: () =>
      getJson<MockData['strategy']['feed']>('/strategies/feed', () => mock.strategy.feed),
    detail: (strategyId: string) =>
      getJson<StrategyDetail>(`/strategies/${encodeURIComponent(strategyId)}`, () => {
        throw new Error('Strategy detail not available in mock')
      }),
    update: (strategyId: string, body: StrategyUpdatePayload) =>
      putJson<StrategyDetail>(`/strategies/${encodeURIComponent(strategyId)}`, body),
    delete: (strategyId: string) =>
      deleteJson(`/strategies/${encodeURIComponent(strategyId)}`),
  },
  backtest: {
    overview: () => getJson<MockData['backtest']>('/backtests/overview', () => mock.backtest),
    runReal: (payload: BacktestCreatePayload) =>
      postJson<BacktestTaskResult>('/backtests/', payload),
    walkForward: (payload: WalkForwardCreatePayload) =>
      postJson<{
        taskId: string
        runId: string
        folds: WalkForwardFoldPayload[]
        aggregate: BacktestMetricPayload
      }>('/backtests/walk-forward', payload),
    sensitivity: (payload: BacktestCreatePayload) =>
      postJson<{ taskId: string; runId: string; runs: SensitivityRunPayload[] }>(
        '/backtests/sensitivity',
        payload,
      ),
    overfit: (taskId: string) =>
      getJson<OverfitAssessmentPayload>(
        `/backtests/${encodeURIComponent(taskId)}/overfit`,
        () => ({ score: 0, level: 'high', components: [] }),
      ),
    trades: (taskId: string) =>
      getJson<BacktestTradePayload[]>(
        `/backtests/${encodeURIComponent(taskId)}/trades`,
        () => [],
      ),
    report: (taskId: string) =>
      getJson<BacktestReportPayload>(
        `/backtests/${encodeURIComponent(taskId)}/report`,
        () => {
          throw new Error('report unavailable')
        },
      ),
    detail: (taskId: string) =>
      getJson<BacktestTaskResult>(
        `/backtests/${encodeURIComponent(taskId)}`,
        () => {
          throw new Error('backtest detail unavailable')
        },
      ),
    list: (limit = 20) =>
      getJson<BacktestTaskListPayload[]>(`/backtests/?limit=${limit}`, () => []),
  },
  explain: {
    overview: () => getJson<MockData['explain']>('/explain/overview', () => mock.explain),
  },
  portfolio: {
    overview: () => getJson<MockData['portfolio']>('/portfolio/overview', () => mock.portfolio),
  },
  execution: {
    overview: () => getJson<MockData['execution']>('/execution/overview', () => mock.execution),
  },
  risk: {
    overview: () => getJson<MockData['risk']>('/risk/overview', () => mock.risk),
  },
  data: {
    overview: () => getJson<MockData['data']>('/data/overview', () => mock.data),
    symbols: () => getJson<SymbolSummary[]>('/data/symbols', () => []),
  },
  security: {
    overview: () => getJson<MockData['security']>('/security/overview', () => mock.security),
  },
  collaboration: {
    overview: () =>
      getJson<MockData['collaboration']>('/collaboration/overview', () => mock.collaboration),
  },
  audit: {
    overview: () => getJson<MockData['audit']>('/audit/overview', () => mock.audit),
  },
  paper: {
    createAccount: (payload: PaperAccountCreatePayload) =>
      postJson<PaperAccount>('/paper/accounts', payload),
    listAccounts: () => getJson<PaperAccount[]>('/paper/accounts', () => []),
    getAccount: (accountId: string) =>
      getJson<PaperAccount>(
        `/paper/accounts/${encodeURIComponent(accountId)}`,
        () => {
          throw new Error('paper account unavailable')
        },
      ),
    positions: (accountId: string) =>
      getJson<PaperPosition[]>(
        `/paper/accounts/${encodeURIComponent(accountId)}/positions`,
        () => [],
      ),
    orders: (accountId: string) =>
      getJson<PaperOrder[]>(
        `/paper/accounts/${encodeURIComponent(accountId)}/orders`,
        () => [],
      ),
    fills: (accountId: string) =>
      getJson<PaperFill[]>(
        `/paper/accounts/${encodeURIComponent(accountId)}/fills`,
        () => [],
      ),
    nav: (accountId: string) =>
      getJson<PaperNavPoint[]>(
        `/paper/accounts/${encodeURIComponent(accountId)}/nav`,
        () => [],
      ),
    breaches: (accountId: string) =>
      getJson<PaperRiskBreach[]>(
        `/paper/accounts/${encodeURIComponent(accountId)}/breaches`,
        () => [],
      ),
    runEod: (accountId: string, tradeDate: string) =>
      postJson<RunEodSummary>(
        `/paper/accounts/${encodeURIComponent(accountId)}/run-eod`,
        { tradeDate },
      ),
  },
}
