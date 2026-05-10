import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const AuditContext = createContext<MockData['audit'] | null>(null)

export const AuditProvider = AuditContext.Provider

export function useAudit() {
  const ctx = useContext(AuditContext)
  if (!ctx) throw new Error('useAudit must be inside AuditProvider')
  return ctx
}
