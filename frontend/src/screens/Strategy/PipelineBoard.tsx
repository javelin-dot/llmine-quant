import { useStrategy } from '../../contexts/StrategyContext'

interface PipelineBoardProps {
  onNavigate?: (target: string) => void
}

function tagClass(c?: string) {
  if (!c) return 'tag'
  return `tag ${c}`
}

export default function PipelineBoard({ onNavigate }: PipelineBoardProps) {
  const data = useStrategy()
  return (
    <div className="pipeline-board-wrap">
      <div className="pipeline-board-head">
        <div>
          <h4 className="pipeline-board-title">策略版本流水线</h4>
          <span className="pipeline-board-sub">从草稿到归档全程可追溯 · 点击卡片跳转回测</span>
        </div>
        <div className="pipeline-board-legend">
          <span><span className="legend-dot dot-blue" />草稿</span>
          <span><span className="legend-dot dot-yellow" />回测</span>
          <span><span className="legend-dot dot-green" />模拟盘</span>
          <span><span className="legend-dot dot-red" />候选</span>
          <span><span className="legend-dot dot-purple" />归档</span>
        </div>
      </div>
      <div className="pipeline-board">
        {data.pipelineBoard.map((lane) => (
          <div className={`pipeline-lane lane-${lane.tone}`} key={lane.lane}>
            <div className="pipeline-lane-head">
              <div className="pipeline-lane-titlewrap">
                <span className={`legend-dot dot-${lane.tone}`} />
                <strong>{lane.lane}</strong>
              </div>
              <span className="pipeline-lane-count">{lane.tickets.length}</span>
            </div>
            <div className="pipeline-lane-body">
              {lane.tickets.map((t) => (
                <button
                  className={`pipeline-ticket ticket-${lane.tone}`}
                  key={t.id}
                  onClick={() => onNavigate?.('backtest')}
                >
                  <div className="pipeline-ticket-head">
                    <strong>{t.title}</strong>
                    <span className={tagClass(t.tagClass)}>{t.tag}</span>
                  </div>
                  <p className="pipeline-ticket-desc">{t.desc}</p>
                  <div className="pipeline-ticket-progress">
                    <div className={`pipeline-ticket-bar bar-${lane.tone}`}>
                      <span style={{ width: `${t.progress}%` }} />
                    </div>
                    <span className="pipeline-ticket-progress-label">{t.progress}%</span>
                  </div>
                  <div className="pipeline-ticket-metrics">
                    {t.metrics.map((m, i) => (
                      <div className="pipeline-ticket-metric" key={i}>
                        <small>{m.label}</small>
                        <strong>{m.value}</strong>
                      </div>
                    ))}
                  </div>
                </button>
              ))}
              {lane.tickets.length === 0 && (
                <div className="pipeline-empty">暂无</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
