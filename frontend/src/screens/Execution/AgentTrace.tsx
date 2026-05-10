import { useExecution } from '../../contexts/ExecutionContext'

export default function AgentTrace() {
  const data = useExecution()
  const trace = data.agentTrace

  return (
    <div className="ex-agenttrace">
      <div className="ex-agenttrace-head">
        <div>
          <h4 className="ex-agenttrace-title">Agent 操作流 · Live Trace</h4>
          <span className="ex-agenttrace-sub">{trace.length} 条 · 实时</span>
        </div>
        <span className="ex-agenttrace-pulse">
          <i />
          LIVE
        </span>
      </div>
      <div className="ex-agenttrace-list">
        {trace.map((t, i) => (
          <div className={`ex-trace-row tone-${t.tone}`} key={i}>
            <span className={`ex-trace-icon icon-${t.tone}`}>{t.icon}</span>
            <div className="ex-trace-body">
              <div className="ex-trace-line">
                <strong>{t.action}</strong>
                <span className="ex-trace-agent">{t.agent}</span>
                <em className="ex-trace-time">{t.time}</em>
              </div>
              <p className="ex-trace-detail">{t.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
