import Agent from './index'

export default function AgentStudioPage() {
  return (
    <div className="agent-standalone-root">
      <header className="agent-standalone-header">
        <div className="agent-standalone-brand">
          <div className="agent-standalone-logo" />
          <div>
            <span className="agent-standalone-eyebrow">LLMine Quant</span>
            <h1>LLMINE QUANT · Agent Console</h1>
          </div>
        </div>
        <div className="agent-standalone-actions">
          <input className="agent-global-search" placeholder="搜索 Agent、Workflow、Run..." />
          <span className="agent-env-badge">DEV</span>
          <span className="status-dot-green" style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block' }} />
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>已连接</span>
          <button
            className="btn secondary"
            onClick={() => window.close()}
            style={{ marginLeft: 8 }}
          >
            关闭
          </button>
        </div>
      </header>
      <div className="agent-standalone-body">
        <Agent />
      </div>
    </div>
  )
}
