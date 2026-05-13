import { createContext, useContext } from 'react'
import type { PaperAccount, PaperNavPoint, PaperPosition, PaperOrder } from '../lib/api'

interface PaperContextValue {
  account: PaperAccount
  nav: PaperNavPoint[]
  positions: PaperPosition[]
  orders: PaperOrder[]
}

const PaperContext = createContext<PaperContextValue | null>(null)

export const PaperProvider = PaperContext.Provider

export function usePaper() {
  const ctx = useContext(PaperContext)
  if (!ctx) throw new Error('usePaper must be inside PaperProvider')
  return ctx
}
