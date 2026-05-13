import { mock } from '../data'
import type { MockData } from '../data/types'

const API_PREFIX = '/api/v1'
const TOKEN_KEY = 'llmine_token'

// ── Auth token store ──────────────────────────────────────────────────────────
let _token: string | null = localStorage.getItem(TOKEN_KEY)

export const authStore = {
  getToken: () => _token,
  setToken: (t: string) => {
    _token = t
    localStorage.setItem(TOKEN_KEY, t)
  },
  clearToken: () => {
    _token = null
    localStorage.removeItem(TOKEN_KEY)
  },
  isAuthenticated: () => _token !== null,
}

function _authHeader(): Record<string, string> {
  return _token ? { Authorization: `Bearer ${_token}` } : {}
}

function _onUnauthorized() {
  authStore.clearToken()
  window.dispatchEvent(new CustomEvent('llmine:unauthorized'))
}

async function getJson<T>(path: string, fallback: () => T): Promise<T> {
  try {
    const res = await fetch(`${API_PREFIX}${path}`, {
      headers: { Accept: 'application/json', ..._authHeader() },
    })
    if (res.status === 401) { _onUnauthorized(); return fallback() }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } catch {
    return fallback()
  }
}

async function postJson<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ..._authHeader() },
    body: JSON.stringify(body),
  })
  if (res.status === 401) { _onUnauthorized(); throw new Error('Unauthorized') }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

async function putJson<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'PUT',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ..._authHeader() },
    body: JSON.stringify(body),
  })
  if (res.status === 401) { _onUnauthorized(); throw new Error('Unauthorized') }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

async function deleteJson(path: string): Promise<void> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json', ..._authHeader() },
  })
  if (res.status === 401) { _onUnauthorized(); throw new Error('Unauthorized') }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string
  name: string
  email: string
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

// MockData['dashboard'] already includes meta/system/modals — use it directly.
type DashboardOverview = MockData['dashboard']

export interface StrategyTemplate {
  id: string
  name: string
  risk: string
  market: string
  family: string
  desc: string
}

export interface StrategyTransitionPayload {
  target: string
  note?: string
}

export interface AuditRow {
  time: string
  actor: string
  actorType: string
  action: string
  resource: string
  result: string
  resultTone: string
  confidence: number
  detail: string
  traceId: string
}

export interface MarketBarImportAksharePayload {
  symbols: string[]
  start_date: string
  end_date: string
  adjust?: string
}

export interface MarketBarDailyOut {
  id: string
  symbol: string
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  adjusted_close: number | null
}

export interface FeatureOut {
  id: string
  name: string
  version: string
  kind: string
  description: string | null
  computationWindow: number | null
  validated: boolean
  permissionScope: string
}

export interface MarketDataImportSummary {
  source: string
  total_rows: number
  imported_rows: number
  inserted_rows: number
  updated_rows: number
  skipped_rows: number
  symbols: string[]
  start_date: string | null
  end_date: string | null
  errors: string[]
}

export const api = {
  auth: {
    login: async (email: string, password: string): Promise<TokenResponse> => {
      const form = new URLSearchParams({ username: email, password })
      const res = await fetch(`${API_PREFIX}/auth/login`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `HTTP ${res.status}`)
      }
      return (await res.json()) as TokenResponse
    },
    register: async (name: string, email: string, password: string): Promise<TokenResponse> => {
      const res = await fetch(`${API_PREFIX}/auth/register`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `HTTP ${res.status}`)
      }
      return (await res.json()) as TokenResponse
    },
    logout: (token: string) =>
      postJson<{ status: string }>('/auth/logout', { access_token: token }),
    refresh: (token: string) =>
      postJson<TokenResponse>('/auth/refresh', { access_token: token }),
    me: () =>
      fetch(`${API_PREFIX}/auth/me`, {
        headers: { Accept: 'application/json', ..._authHeader() },
      }).then(r => r.ok ? r.json() : null),
  },
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
    createDraft: (payload: {
      name: string
      family: string
      type?: string
      description?: string | null
      riskProfile: string
      market: string
      universe?: string | null
      frequency?: string
    }) => postJson<{ strategy_id: string; status: string }>('/strategies/', payload),
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
    templates: () =>
      getJson<StrategyTemplate[]>('/strategies/templates', () => []),
    events: (strategyId: string) =>
      getJson<{ id: string; stage: string; event: string; progress: number; createdAt: string }[]>(
        `/strategies/${encodeURIComponent(strategyId)}/events`,
        () => [],
      ),
    transition: (strategyId: string, payload: StrategyTransitionPayload) =>
      postJson<{ strategy_id: string; status: string }>(
        `/strategies/${encodeURIComponent(strategyId)}/transition`,
        payload,
      ),
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
    approveRebalance: (proposalId: string) =>
      postJson<{ proposal_id: string; status: string }>(
        `/portfolio/rebalance/${encodeURIComponent(proposalId)}/approve`,
        {},
      ),
  },
  execution: {
    overview: () => getJson<MockData['execution']>('/execution/overview', () => mock.execution),
    approve: (approvalId: string) =>
      postJson<{ approval_id: string; status: string }>(
        `/execution/approvals/${encodeURIComponent(approvalId)}/approve`,
        {},
      ),
    reject: (approvalId: string, reason?: string) =>
      postJson<{ approval_id: string; status: string }>(
        `/execution/approvals/${encodeURIComponent(approvalId)}/reject`,
        { reason: reason ?? '' },
      ),
  },
  risk: {
    overview: () => getJson<MockData['risk']>('/risk/overview', () => mock.risk),
    triggerCircuit: (level: string) =>
      postJson<{ level: string; status: string }>(
        `/risk/circuit-breakers/${encodeURIComponent(level)}/trigger`,
        {},
      ),
    recoverCircuit: (level: string) =>
      postJson<{ level: string; status: string }>(
        `/risk/circuit-breakers/${encodeURIComponent(level)}/recover`,
        {},
      ),
  },
  data: {
    overview: () => getJson<MockData['data']>('/data/overview', () => mock.data),
    symbols: () => getJson<SymbolSummary[]>('/data/symbols', () => []),
    marketBars: (symbol?: string, startDate?: string, endDate?: string, limit = 500) => {
      const params = new URLSearchParams()
      if (symbol) params.set('symbol', symbol)
      if (startDate) params.set('startDate', startDate)
      if (endDate) params.set('endDate', endDate)
      params.set('limit', String(limit))
      return getJson<MarketBarDailyOut[]>(`/data/market-bars?${params}`, () => [])
    },
    importAkshare: (payload: MarketBarImportAksharePayload) =>
      postJson<MarketDataImportSummary>('/data/market-bars/import/akshare', payload),
    features: () => getJson<FeatureOut[]>('/data/features', () => []),
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
    logs: (actorType?: string, limit = 50, offset = 0) => {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
      if (actorType) params.set('actor_type', actorType)
      return getJson<AuditRow[]>(`/audit/logs?${params}`, () => [])
    },
    registry: () => getJson<{ name: string; level: string; levelTone: string; desc: string; agents: string[] }[]>('/audit/registry', () => []),
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
