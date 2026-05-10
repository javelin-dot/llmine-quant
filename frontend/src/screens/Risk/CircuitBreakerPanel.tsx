import { useRisk } from '../../contexts/RiskContext'

const STATUS_LABEL: Record<string, string> = {
  armed: 'ARMED',
  triggered: 'TRIGGERED',
  cooldown: 'COOLDOWN',
  disabled: 'DISABLED',
}

const STATUS_ICON: Record<string, string> = {
  armed: '◉',
  triggered: '◯',
  cooldown: '◐',
  disabled: '◌',
}

interface PanelProps {
  onModal?: (target: string) => void
}

export default function CircuitBreakerPanel({ onModal }: PanelProps) {
  const data = useRisk()
  const list = data.circuits
  const triggeredCount = list.filter((c) => c.status === 'triggered').length

  return (
    <div className="rk-circuit">
      <div className="rk-circuit-head">
        <div>
          <h4 className="rk-circuit-title">熔断阶梯 · Circuit Breakers</h4>
          <span className="rk-circuit-sub">
            L1-L4 四级熔断 · {triggeredCount > 0 ? <em className="warn">{triggeredCount} 级激活</em> : <em className="ok">全部待命</em>}
          </span>
        </div>
        <div className="rk-circuit-actions">
          <button className="rk-circuit-btn ghost">规则配置</button>
          <button className="rk-circuit-btn danger" onClick={() => onModal?.('kill')}>L4 全局</button>
        </div>
      </div>

      <div className="rk-circuit-rail">
        {list.map((c, i) => {
          const triggered = c.status === 'triggered'
          return (
            <article
              className={`rk-circuit-card status-${c.status} tone-${c.statusTone} level-${c.level.toLowerCase()}`}
              key={c.level}
            >
              <header className="rk-circuit-card-head">
                <div className="rk-circuit-level">
                  <span className={`rk-circuit-icon icon-${c.statusTone}`}>{STATUS_ICON[c.status]}</span>
                  <strong>{c.name}</strong>
                </div>
                <span className={`rk-circuit-status pill-${c.statusTone}`}>
                  {STATUS_LABEL[c.status]}
                </span>
              </header>

              <div className="rk-circuit-rule">
                <small>触发</small>
                <p>{c.trigger}</p>
              </div>
              <div className="rk-circuit-rule">
                <small>动作</small>
                <p>{c.action}</p>
              </div>

              <footer className="rk-circuit-card-foot">
                <div className="rk-circuit-foot-cell">
                  <small>24h 触发</small>
                  <strong className={c.triggers24h > 0 ? 'warn' : ''}>{c.triggers24h}</strong>
                </div>
                <div className="rk-circuit-foot-cell">
                  <small>最近</small>
                  <strong className={triggered ? 'warn' : ''}>{c.lastTrigger}</strong>
                </div>
              </footer>

              {triggered && <span className="rk-circuit-glow" />}
              {i < list.length - 1 && <span className="rk-circuit-connector" />}
            </article>
          )
        })}
      </div>
    </div>
  )
}
