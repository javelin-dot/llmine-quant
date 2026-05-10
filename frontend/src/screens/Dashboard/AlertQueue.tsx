import { useState } from 'react'
import { useDashboard } from '../../contexts/DashboardContext'

type AlertType = 'approval' | 'risk' | 'system'

interface AlertQueueProps {
  onNavigate?: (target: string) => void
}

const TYPE_META: Record<AlertType, { label: string; icon: string; color: string }> = {
  approval: { label: '待审批', icon: '✓', color: 'yellow' },
  risk: { label: '风险告警', icon: '⚠', color: 'red' },
  system: { label: '系统', icon: 'ⓘ', color: 'blue' },
}

export default function AlertQueue({ onNavigate }: AlertQueueProps) {
  const data = useDashboard()
  const alerts = data.alerts
  const [activeTab, setActiveTab] = useState<AlertType>('approval')

  const counts: Record<AlertType, number> = {
    approval: alerts.filter((a) => a.type === 'approval').length,
    risk: alerts.filter((a) => a.type === 'risk').length,
    system: alerts.filter((a) => a.type === 'system').length,
  }

  const filtered = alerts.filter((a) => a.type === activeTab)

  return (
    <div className="alert-queue">
      <div className="alert-queue-head">
        <h4 className="alert-queue-title">Alerts & Queue</h4>
      </div>
      <div className="alert-queue-tabs">
        {(Object.keys(TYPE_META) as AlertType[]).map((t) => {
          const meta = TYPE_META[t]
          const active = t === activeTab
          return (
            <button
              key={t}
              className={`alert-tab ${active ? 'active' : ''} alert-tab-${meta.color}`}
              onClick={() => setActiveTab(t)}
            >
              <span className="alert-tab-icon">{meta.icon}</span>
              <span className="alert-tab-label">{meta.label}</span>
              <span className={`alert-tab-badge alert-tab-badge-${meta.color}`}>{counts[t]}</span>
            </button>
          )
        })}
      </div>
      <ul className="alert-queue-list">
        {filtered.length === 0 && <li className="alert-empty">无{TYPE_META[activeTab].label}事项</li>}
        {filtered.map((a) => (
          <li
            key={a.id}
            className={`alert-item severity-${a.severity}`}
            onClick={() => a.target && onNavigate?.(a.target)}
          >
            <span className={`alert-severity sev-${a.severity}`} />
            <div className="alert-content">
              <strong className="alert-title">{a.title}</strong>
              <span className="alert-time">{a.time}</span>
            </div>
            {a.target && <span className="alert-arrow">›</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}
