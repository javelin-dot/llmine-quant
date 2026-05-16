import { useDashboard } from '../../contexts/DashboardContext'

interface DashboardSystemBarProps {
  onModal?: (target: string) => void
}

export default function DashboardSystemBar({ onModal }: DashboardSystemBarProps) {
  const { system } = useDashboard()

  return (
    <div className="dashboard-system-bar">
      <span className="pill">
        <span className="dot" /> AI Autopilot {system.autopilot ? 'ON' : 'OFF'}
      </span>
      <span className="pill">{system.riskGateLabel}</span>
      <button type="button" className="btn secondary" onClick={() => onModal?.('global')}>
        全局概览
      </button>
      <button type="button" className="btn danger" onClick={() => onModal?.('kill')}>
        Kill Switch
      </button>
    </div>
  )
}
