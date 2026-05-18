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

function _detailFromBody(text: string, status: number): string {
  const fallback = text || `HTTP ${status}`
  try {
    const parsed = JSON.parse(text) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
    return fallback
  } catch {
    return fallback
  }
}

async function getJsonStrict<T>(path: string): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    headers: { Accept: 'application/json', ..._authHeader() },
  })
  if (res.status === 401) {
    _onUnauthorized()
    throw new Error('Unauthorized')
  }
  const text = await res.text().catch(() => '')
  if (!res.ok) throw new Error(_detailFromBody(text, res.status))
  return (text ? (JSON.parse(text) as T) : ({} as T))
}

async function patchJson<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: 'PATCH',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ..._authHeader() },
    body: JSON.stringify(body),
  })
  if (res.status === 401) {
    _onUnauthorized()
    throw new Error('Unauthorized')
  }
  const text = await res.text().catch(() => '')
  if (!res.ok) throw new Error(_detailFromBody(text, res.status))
  return (text ? (JSON.parse(text) as T) : ({} as T))
}

export interface AuthMe {
  user_id: string
  email: string
  name: string
  status: string
  roles: string[]
  is_admin?: boolean
}

export interface AdminUserRow {
  user_id: string
  email: string
  name: string
  status: string
  roles: string[]
}

export interface AdminRoleRow {
  id: string
  name: string
  description: string | null
}

export interface InviteUserResponse {
  user_id: string
  email: string
  name: string
  initial_password: string
  role_name: string
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
  calmarRatio: number
  sortinoRatio: number
  volatility: number
  profitFactor: number
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
  monthlyReturns: Record<string, number>
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
  name?: string | null
  bars: number
  startDate: string
  endDate: string
}

export interface SymbolStatsOut {
  totalSymbols: number
  totalBars: number
  latestTradeDate: string | null
  earliestTradeDate: string | null
}

export interface StockInfoRefreshOut {
  upserted: number
  syncedAt: string
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
  labChecklist: BacktestLabCheckPayload[]
  promotionGate: BacktestPromotionGatePayload | null
}

export interface BacktestLabCheckPayload {
  id: string
  label: string
  status: 'pass' | 'warn' | 'fail'
  detail: string
}

export interface BacktestPromotionGatePayload {
  decision: 'pass' | 'review' | 'block'
  label: string
  readinessScore: number
  reasons: string[]
  nextActions: string[]
}

export interface BacktestCreatePayload {
  universe: string[]
  startDate: string
  endDate: string
  strategyName?: string
  strategyId?: string
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

export type SensitivityCreatePayload = BacktestCreatePayload

// ── Strategy Factory list item (for Backtest Lab strategy selector) ──────────
export interface StrategyListItem {
  id: string
  name: string
  family: string
  type: string
  status: string
  riskProfile: string
  market: string
  sharpe: number | null
  maxDd: number | null
  annualReturn: number | null
  oosScore: number | null
  updatedAt: string
}

// ── Universe suggestion (三步选股法) ──────────────────────────────────────────
export interface UniverseSuggestCriteria {
  strategyFamily?: string
  maxSymbols?: number
  diversify?: boolean
  // Step 1 — 流动性
  indexPool?: 'csi300' | 'csi500' | 'csi1000' | 'both' | 'all'
  boards?: ('main' | 'star' | 'chinext' | 'bse')[]
  sectors?: string[]
  minBars?: number
  minAvgTurnoverCny?: number
  // Step 2 — 波动率
  minVolatility?: number
  maxVolatility?: number
  // Step 3 — 动量
  momentumWindowDays?: number
  minMomentum?: number
  maxMomentum?: number
}

export interface UniverseCandidate {
  symbol: string
  name: string | null
  bars: number
  startDate: string
  endDate: string
  coverageDays: number
  selected: boolean
  reason: string | null  // AI-generated selection / exclusion reason
  avgTurnover?: number | null
  volatility?: number | null
  momentum?: number | null
  dropReason?: string | null
}

export interface UniverseSuggestResult {
  symbols: string[]
  candidates: UniverseCandidate[]
  diversityScore: number
  coverageDays: number
  recommendation: string
  aiRationale: string | null  // overall AI rationale
  aiModel: string | null      // which model generated this
  totalPool?: number          // size of the raw candidate pool (pre-filter)
  totalEligible?: number      // passed all three steps
  totalRejected?: number      // failed any of the three steps
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

export interface PaperAccountBindStrategyPayload {
  strategyId: string
  strategyVersionId: string
}

export interface PaperPosition {
  symbol: string
  quantity: number
  availableQuantity: number
  todayBuyQuantity: number
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

export interface ManualPaperOrderPayload {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  tradeDate?: string
  reason?: string
  executionMode?: 'immediate' | 'queue'
}

export interface PaperTargetPosition {
  symbol: string
  targetWeight: number
  currentWeight: number
  driftWeight: number
  targetQuantity: number
  currentQuantity: number
  recommendedAction: 'open' | 'increase' | 'decrease' | 'close' | 'hold'
  reason: string | null
}

export interface PaperEvaluationSnapshot {
  tradeDate: string | null
  sessionStatus: string
  strategyBound: boolean
  targetGross: number
  currentGross: number
  driftGross: number
  targets: PaperTargetPosition[]
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

export interface AgentDefinition {
  id: string
  name: string
  role: string
  avatar: string
  description: string
  objective: string
  downstreamHint: string
  autonomy: string
  status: string
  modelConfig: Record<string, unknown>
  systemPrompt: string
  userPromptTemplate: string
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
  normalizedInputSchema: Record<string, unknown>
  normalizedOutputSchema: Record<string, unknown>
  inputMapping: Record<string, unknown>[]
  outputMapping: Record<string, unknown>[]
  toolPolicy: Record<string, unknown>[]
  constraints: Record<string, unknown>[]
  runtimePolicy: Record<string, unknown>
}

export interface WorkflowNode {
  id: string
  agentDefinitionId: string
  label: string | null
  positionX: number
  positionY: number
  configOverride: Record<string, unknown>
}

export interface WorkflowEdge {
  id: string
  sourceNodeId: string
  targetNodeId: string
  mapping: Record<string, unknown>[]
  condition: Record<string, unknown>
}

export interface AgentWorkflow {
  id: string
  name: string
  description: string
  version: string
  status: string
  isDefault: boolean
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export interface WorkflowVersion {
  id: string
  workflowId: string
  version: string
  status: string
  publishedAt: string
  snapshot: Record<string, unknown>
}

export interface WorkflowPublishResult {
  workflow: AgentWorkflow
  version: WorkflowVersion
}

export interface WorkflowRunResult {
  workflowId: string
  traceId: string
  result: {
    current?: Record<string, unknown>
    nodeResults?: Record<string, Record<string, unknown>>
    history?: { agent: string; result: Record<string, unknown> }[]
  }
}

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
  tradeDate: string
  prevClose: number | null
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  adjustedClose: number | null
  isSt?: boolean
  isLimitUp?: boolean
  isLimitDown?: boolean
  isSuspended?: boolean
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
  totalRows: number
  importedRows: number
  insertedRows: number
  updatedRows: number
  skippedRows: number
  symbols: string[]
  startDate: string | null
  endDate: string | null
  errors: string[]
}

export type MarketSyncPhase = 'idle' | 'scanning' | 'syncing' | 'retrying' | 'st_flags' | 'completed' | 'failed'

export interface MarketSyncStatus {
  taskId: string | null
  phase: MarketSyncPhase
  startedAt: string | null
  finishedAt: string | null
  total: number
  done: number
  skipped: number
  insertedRows: number
  updatedRows: number
  failures: number
  ratePerSec: number
  etaSeconds: number | null
  lastSymbol: string | null
  error: string | null
  isRunning: boolean
}

export interface MarketSyncStartPayload {
  startDate?: string
  endDate?: string
  adjust?: 'qfq' | 'hfq' | 'none'
  concurrency?: number
  boards?: string[]
  incremental?: boolean
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
    me: async (): Promise<AuthMe | null> => {
      try {
        const res = await fetch(`${API_PREFIX}/auth/me`, {
          headers: { Accept: 'application/json', ..._authHeader() },
        })
        if (res.status === 401) {
          _onUnauthorized()
          return null
        }
        if (!res.ok) return null
        const j = (await res.json()) as {
          user_id?: string
          email?: string
          name?: string
          status?: string
          roles?: unknown
          is_admin?: unknown
        }
        const rolesRaw = j.roles
        const roles = Array.isArray(rolesRaw)
          ? rolesRaw.filter((x): x is string => typeof x === 'string')
          : []
        return {
          user_id: String(j.user_id ?? ''),
          email: String(j.email ?? ''),
          name: String(j.name ?? ''),
          status: String(j.status ?? ''),
          roles,
          is_admin: j.is_admin === true,
        }
      } catch {
        return null
      }
    },
    listUsers: () => getJsonStrict<AdminUserRow[]>('/auth/users'),
    listRoles: () => getJsonStrict<AdminRoleRow[]>('/auth/roles'),
    inviteUser: (payload: { name: string; email: string; role_name: string; password?: string }) =>
      postJson<InviteUserResponse>('/auth/users', payload),
    updateUser: (userId: string, payload: { name?: string; status?: string }) =>
      patchJson<AdminUserRow>(`/auth/users/${encodeURIComponent(userId)}`, payload),
  },
  dashboard: {
    overview: () =>
      getJson<DashboardOverview>('/dashboard/overview', () => mock.dashboard),
  },
  agent: {
    definitions: () => getJson<AgentDefinition[]>('/agents/definitions', () => []),
    createDefinition: (payload: Omit<AgentDefinition, 'id'>) =>
      postJson<AgentDefinition>('/agents/definitions', payload),
    updateDefinition: (id: string, payload: Omit<AgentDefinition, 'id'>) =>
      putJson<AgentDefinition>(`/agents/definitions/${id}`, payload),
    deleteDefinition: (id: string) => deleteJson(`/agents/definitions/${id}`),
    workflows: () => getJson<AgentWorkflow[]>('/agents/workflows', () => []),
    createWorkflow: (payload: Omit<AgentWorkflow, 'id'>) =>
      postJson<AgentWorkflow>('/agents/workflows', payload),
    updateWorkflow: (id: string, payload: Omit<AgentWorkflow, 'id'>) =>
      putJson<AgentWorkflow>(`/agents/workflows/${id}`, payload),
    workflowVersions: (id: string) =>
      getJson<WorkflowVersion[]>(`/agents/workflows/${id}/versions`, () => []),
    publishWorkflow: (id: string) =>
      postJson<WorkflowPublishResult>(`/agents/workflows/${id}/publish`, {}),
    runWorkflow: (id: string, payload: { traceId?: string; payload: Record<string, unknown> }) =>
      postJson<WorkflowRunResult>(`/agents/workflows/${id}/run`, payload),
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
    backtestReady: () =>
      getJson<{ total: number; items: StrategyListItem[] }>('/strategies/backtest-ready', () => ({ total: 0, items: [] })),
    list: () =>
      getJson<{ total: number; items: StrategyListItem[] }>('/strategies?page_size=100', () => ({ total: 0, items: [] })),
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
    suggestUniverse: (criteria: UniverseSuggestCriteria) =>
      postJson<UniverseSuggestResult>('/backtests/universe/suggest', {
        strategyFamily: criteria.strategyFamily ?? 'trend',
        maxSymbols: criteria.maxSymbols ?? 20,
        diversify: criteria.diversify ?? true,
        indexPool: criteria.indexPool ?? 'both',
        boards: criteria.boards ?? [],
        sectors: criteria.sectors ?? [],
        minBars: criteria.minBars ?? 60,
        minAvgTurnoverCny: criteria.minAvgTurnoverCny ?? 1e8,
        minVolatility: criteria.minVolatility ?? 0.10,
        maxVolatility: criteria.maxVolatility ?? 0.80,
        momentumWindowDays: criteria.momentumWindowDays ?? 60,
        minMomentum: criteria.minMomentum ?? -0.20,
        maxMomentum: criteria.maxMomentum ?? 2.0,
      }),
    sectorList: () =>
      getJson<{ name: string; count: number }[]>('/backtests/universe/sectors', () => []),
  },
  explain: {
    overview: () => getJsonStrict<MockData['explain']>('/explain/overview'),
    approveSignal: (traceId: string) =>
      postJson<{ traceId: string; status: string }>('/explain/signal/approve', {
        traceId,
      }),
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
    symbols: (
      params: { search?: string; sort?: 'bars' | 'symbol' | 'recent'; offset?: number; limit?: number } = {},
    ) => {
      const sp = new URLSearchParams()
      if (params.search) sp.set('search', params.search)
      if (params.sort) sp.set('sort', params.sort)
      if (params.offset != null) sp.set('offset', String(params.offset))
      if (params.limit != null) sp.set('limit', String(params.limit))
      const qs = sp.toString()
      return getJson<SymbolSummary[]>(`/data/symbols${qs ? `?${qs}` : ''}`, () => [])
    },
    symbolsStats: () =>
      getJson<SymbolStatsOut>('/data/symbols/stats', () => ({
        totalSymbols: 0,
        totalBars: 0,
        latestTradeDate: null,
        earliestTradeDate: null,
      })),
    marketBars: (
      symbol?: string,
      startDate?: string,
      endDate?: string,
      limit = 10,
      offset = 0,
      order: 'asc' | 'desc' = 'desc',
    ) => {
      const params = new URLSearchParams()
      if (symbol) params.set('symbol', symbol)
      if (startDate) params.set('startDate', startDate)
      if (endDate) params.set('endDate', endDate)
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      params.set('order', order)
      return getJson<MarketBarDailyOut[]>(`/data/market-bars?${params}`, () => [])
    },
    importAkshare: (payload: MarketBarImportAksharePayload) =>
      postJson<MarketDataImportSummary>('/data/market-bars/import/akshare', payload),
    features: () => getJson<FeatureOut[]>('/data/features', () => []),
    syncStatus: () =>
      getJson<MarketSyncStatus>('/data/market-bars/sync/status', () => ({
        taskId: null, phase: 'idle', startedAt: null, finishedAt: null,
        total: 0, done: 0, skipped: 0, insertedRows: 0, updatedRows: 0,
        failures: 0, ratePerSec: 0, etaSeconds: null, lastSymbol: null,
        error: null, isRunning: false,
      })),
    triggerSync: (payload: MarketSyncStartPayload = {}) =>
      postJson<MarketSyncStatus>('/data/market-bars/sync/full', payload),
    refreshStockInfo: () =>
      postJson<StockInfoRefreshOut>('/data/stock-info/refresh', {}),
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
    bindStrategy: (accountId: string, payload: PaperAccountBindStrategyPayload) =>
      putJson<PaperAccount>(
        `/paper/accounts/${encodeURIComponent(accountId)}/strategy`,
        payload,
      ),
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
    submitOrder: (accountId: string, payload: ManualPaperOrderPayload) =>
      postJson<PaperOrder>(
        `/paper/accounts/${encodeURIComponent(accountId)}/orders`,
        payload,
      ),
    replaceOrder: (accountId: string, orderId: string, quantity: number) =>
      patchJson<PaperOrder>(
        `/paper/accounts/${encodeURIComponent(accountId)}/orders/${encodeURIComponent(orderId)}`,
        { quantity },
      ),
    cancelOrder: (accountId: string, orderId: string) =>
      postJson<PaperOrder>(
        `/paper/accounts/${encodeURIComponent(accountId)}/orders/${encodeURIComponent(orderId)}/cancel`,
        {},
      ),
    matchOrders: (accountId: string, tradeDate?: string) =>
      postJson<{ ordersFilled: number; ordersRejected: number }>(
        `/paper/accounts/${encodeURIComponent(accountId)}/orders/match`,
        tradeDate ? { tradeDate } : {},
      ),
    evaluation: (accountId: string) =>
      getJson<PaperEvaluationSnapshot>(
        `/paper/accounts/${encodeURIComponent(accountId)}/evaluation`,
        () => ({
          tradeDate: null,
          sessionStatus: 'closed',
          strategyBound: false,
          targetGross: 0,
          currentGross: 0,
          driftGross: 0,
          targets: [],
        }),
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
