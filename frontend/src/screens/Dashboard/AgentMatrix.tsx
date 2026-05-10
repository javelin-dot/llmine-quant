import { useDashboard } from '../../contexts/DashboardContext'

const STATUS_LABEL: Record<string, string> = {
  active: '运行中',
  waiting: '等待中',
  attention: '需注意',
  idle: '空闲',
}

export default function AgentMatrix() {
  const data = useDashboard()
  const agents = data.agents
  const activeCount = agents.filter((a) => a.status === 'active').length

  return (
    <div className="agent-matrix">
      <div className="agent-matrix-head">
        <div>
          <h4 className="agent-matrix-title">Agent Swarm</h4>
          <span className="agent-matrix-sub">{agents.length} agents · {activeCount} active</span>
        </div>
        <span className="agent-matrix-status">
          <span className="agent-matrix-pulse" />
          LIVE
        </span>
      </div>
      <div className="agent-matrix-grid">
        {agents.map((a) => (
          <button className="agent-cell" key={a.name}>
            <div className="agent-cell-row">
              <span className={`status-dot status-${a.status}`} />
              <span className="agent-cell-avatar">{a.avatar}</span>
              <span className="agent-cell-metric">{a.metric}</span>
            </div>
            <strong className="agent-cell-name">{a.name}</strong>
            <span className="agent-cell-detail">{a.detail}</span>
            <span className="agent-cell-status-label">{STATUS_LABEL[a.status]}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
