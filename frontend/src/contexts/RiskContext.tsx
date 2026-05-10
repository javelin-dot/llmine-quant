import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const RiskContext = createContext<MockData['risk'] | null>(null)

export const RiskProvider = RiskContext.Provider

export function useRisk() {
  const ctx = useContext(RiskContext)
  if (!ctx) throw new Error('useRisk must be inside RiskProvider')
  return ctx
}
