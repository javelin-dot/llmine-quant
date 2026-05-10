import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const PortfolioContext = createContext<MockData['portfolio'] | null>(null)

export const PortfolioProvider = PortfolioContext.Provider

export function usePortfolio() {
  const ctx = useContext(PortfolioContext)
  if (!ctx) throw new Error('usePortfolio must be inside PortfolioProvider')
  return ctx
}
