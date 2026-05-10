import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const DataContext = createContext<MockData['data'] | null>(null)

export const DataProvider = DataContext.Provider

export function useData() {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData must be inside DataProvider')
  return ctx
}
