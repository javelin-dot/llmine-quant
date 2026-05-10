import { useDashboard } from '../../contexts/DashboardContext'

interface QuickActionsProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function QuickActions({ onNavigate, onModal }: QuickActionsProps) {
  const data = useDashboard()
  const pending = data.pendingApprovals
  return (
    <div className="quick-actions">
      <button
        className="quick-action quick-action-primary"
        onClick={() => onModal?.('create')}
      >
        <span className="quick-action-icon">+</span>
        <span className="quick-action-label">新建策略</span>
      </button>
      <button
        className="quick-action quick-action-success"
        onClick={() => onNavigate?.('backtest')}
      >
        <span className="quick-action-icon">▶</span>
        <span className="quick-action-label">批量回测</span>
      </button>
      <button
        className="quick-action quick-action-purple"
        onClick={() => onNavigate?.('risk')}
      >
        <span className="quick-action-icon">⚡</span>
        <span className="quick-action-label">风控检查</span>
      </button>
      <button
        className="quick-action quick-action-warn"
        onClick={() => onNavigate?.('execution')}
      >
        <span className="quick-action-icon">✓</span>
        <span className="quick-action-label">审批中心</span>
        {pending > 0 && <span className="quick-action-badge">{pending}</span>}
      </button>
    </div>
  )
}
