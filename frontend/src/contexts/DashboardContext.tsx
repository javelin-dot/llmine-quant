import { createContext, useContext } from 'react'
import type { MockData } from '../data/types'

const DashboardContext = createContext<MockData['dashboard'] | null>(null)

export const DashboardProvider = DashboardContext.Provider

export function useDashboard() {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboard must be inside DashboardProvider')
  return ctx
}
