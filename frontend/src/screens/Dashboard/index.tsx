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
import DashboardSystemBar from './DashboardSystemBar'

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

  const overviewEmpty =
    data.marketIndices.length === 0 &&
    data.strategies.length === 0 &&
    data.alerts.length === 0 &&
    data.agents.length === 0

  return (
    <DashboardProvider value={data}>
      <div className="dashboard-root">
        {overviewEmpty ? (
          <div className="bt-empty-line" style={{ padding: '0.65rem 1rem', opacity: 0.85 }}>
            暂无仪表盘业务数据（行情、策略、告警等为实时聚合结果）。连接后端并产生数据后即可展示。
          </div>
        ) : null}
        <DashboardSystemBar onModal={onModal} />
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
