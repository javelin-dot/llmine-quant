import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { DashboardProvider } from '../../contexts/DashboardContext'
import MarketBar from './MarketBar'
import PortfolioChart from './PortfolioChart'
import AgentMatrix from './AgentMatrix'
import AlertQueue from './AlertQueue'
import StrategyGrid from './StrategyGrid'
import QuickActions from './QuickActions'

interface DashboardProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Dashboard({ onNavigate, onModal }: DashboardProps) {
  const [data, setData] = useState<MockData['dashboard'] | null>(null)

  useEffect(() => {
    api.dashboard.overview()
      .then(setData)
      .catch((e) => console.error('Dashboard API error:', e))
  }, [])

  if (!data) return <div className="dashboard-root">Loading Dashboard…</div>

  return (
    <DashboardProvider value={data}>
      <div className="dashboard-root">
        <MarketBar />
        <div className="dashboard-main">
          <div className="dashboard-main-left">
            <PortfolioChart />
          </div>
          <div className="dashboard-main-right">
            <AgentMatrix />
            <AlertQueue onNavigate={onNavigate} />
          </div>
        </div>
        <StrategyGrid onNavigate={onNavigate} />
        <QuickActions onNavigate={onNavigate} onModal={onModal} />
      </div>
    </DashboardProvider>
  )
}
