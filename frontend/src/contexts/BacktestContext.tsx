import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const BacktestContext = createContext<MockData['backtest'] | null>(null)

export const BacktestProvider = BacktestContext.Provider

export function useBacktest() {
  const ctx = useContext(BacktestContext)
  if (!ctx) throw new Error('useBacktest must be inside BacktestProvider')
  return ctx
}
