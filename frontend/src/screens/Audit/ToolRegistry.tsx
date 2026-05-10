import { mock } from '../../data'

export default function ToolRegistry() {
  const tools = mock.audit.toolRegistry

  return (
    <div className="audit-tools">
      <div className="at-head">
        <div>
          <h4 className="at-title">Agent Tool Registry</h4>
          <span className="at-sub">{tools.length} 个工具 · 权限分级 L1-L6</span>
        </div>
      </div>
      <div className="at-list">
        {tools.map((t, i) => (
          <div className={`at-row tone-${t.levelTone}`} key={i}>
            <div className="at-row-left">
              <span className={`at-level pill-${t.levelTone}`}>{t.level}</span>
              <div className="at-info">
                <strong>{t.name}</strong>
                <span>{t.desc}</span>
              </div>
            </div>
            <div className="at-agents">
              {t.agents.length === 0 ? (
                <span className="at-none">禁止</span>
              ) : (
                t.agents.map((a, j) => (
                  <span className="at-agent" key={j}>{a}</span>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
