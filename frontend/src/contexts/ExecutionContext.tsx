import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const ExecutionContext = createContext<MockData['execution'] | null>(null)

export const ExecutionProvider = ExecutionContext.Provider

export function useExecution() {
  const ctx = useContext(ExecutionContext)
  if (!ctx) throw new Error('useExecution must be inside ExecutionProvider')
  return ctx
}
