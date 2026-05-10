import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const SecurityContext = createContext<MockData['security'] | null>(null)

export const SecurityProvider = SecurityContext.Provider

export function useSecurity() {
  const ctx = useContext(SecurityContext)
  if (!ctx) throw new Error('useSecurity must be inside SecurityProvider')
  return ctx
}
