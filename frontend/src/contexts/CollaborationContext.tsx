import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const CollaborationContext = createContext<MockData['collaboration'] | null>(null)

export const CollaborationProvider = CollaborationContext.Provider

export function useCollaboration() {
  const ctx = useContext(CollaborationContext)
  if (!ctx) throw new Error('useCollaboration must be inside CollaborationProvider')
  return ctx
}
