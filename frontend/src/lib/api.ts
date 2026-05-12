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
  versions: { version: string; codeText: string | null }[]
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
        error: string | null
      }>(`/strategies/tasks/${encodeURIComponent(taskId)}`, () => ({
        id: taskId,
        status: 'failed',
        progress: 100,
        stage: 'failed',
        strategyId: null,
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
}
