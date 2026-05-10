import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const ExplainContext = createContext<MockData['explain'] | null>(null)

export const ExplainProvider = ExplainContext.Provider

export function useExplain() {
  const ctx = useContext(ExplainContext)
  if (!ctx) throw new Error('useExplain must be inside ExplainProvider')
  return ctx
}
