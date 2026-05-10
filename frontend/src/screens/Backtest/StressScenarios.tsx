import { mock } from '../../data'

const SEVERITY_META: Record<string, { label: string; tone: string }> = {
  high: { label: 'HIGH', tone: 'red' },
  medium: { label: 'MED', tone: 'yellow' },
  low: { label: 'LOW', tone: 'green' },
}

interface StressScenariosProps {
  onNavigate?: (target: string) => void
}

export default function StressScenarios({ onNavigate }: StressScenariosProps) {
  const scenarios = mock.backtest.scenarios
  return (
    <div className="bt-scenarios">
      <div className="bt-scenarios-head">
        <div>
          <h4 className="bt-scenarios-title">Stress Scenarios</h4>
          <span className="bt-scenarios-sub">极端场景压力测试 · 不止看收益，看可执行性</span>
        </div>
      </div>
      <div className="bt-scenarios-grid">
        {scenarios.map((s) => {
          const sev = SEVERITY_META[s.severity]
          return (
            <div
              key={s.id}
              className={`bt-scenario tone-${s.fuseTone}`}
              onClick={() => onNavigate?.('risk')}
            >
              <div className="bt-scenario-head">
                <div>
                  <span className={`bt-scenario-sev sev-${sev.tone}`}>{sev.label}</span>
                  <strong className="bt-scenario-name">{s.name}</strong>
                </div>
                <span className={`bt-scenario-fuse fuse-${s.fuseTone}`}>{s.fuse}</span>
              </div>
              <div className="bt-scenario-metrics">
                <div className="bt-scenario-metric">
                  <span>组合损失</span>
                  <strong className="neg">{s.loss}</strong>
                </div>
                <div className="bt-scenario-metric">
                  <span>最大回撤</span>
                  <strong className="neg">{s.maxDd}</strong>
                </div>
                <div className="bt-scenario-metric">
                  <span>人工介入</span>
                  <strong className={s.human === '需要' ? 'warn' : ''}>{s.human}</strong>
                </div>
              </div>
              <p className="bt-scenario-suggestion">
                <span>AI 建议</span>
                {s.suggestion}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
