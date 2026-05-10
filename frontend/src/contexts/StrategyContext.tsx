import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const StrategyContext = createContext<MockData['strategy'] | null>(null)

export const StrategyProvider = StrategyContext.Provider

export function useStrategy() {
  const ctx = useContext(StrategyContext)
  if (!ctx) throw new Error('useStrategy must be inside StrategyProvider')
  return ctx
}
