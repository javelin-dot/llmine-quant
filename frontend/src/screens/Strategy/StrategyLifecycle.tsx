import { useState, useMemo } from 'react'
import { useStrategy } from '../../contexts/StrategyContext'

interface StrategyLifecycleProps {
  strategyId?: string | null
}

const LIFECYCLE_STAGES = [
  { key: 'draft', label: '草稿', tone: 'blue' as const },
  { key: 'research', label: '研究', tone: 'purple' as const },
  { key: 'backtest', label: '回测', tone: 'yellow' as const },
  { key: 'risk_review', label: '风控审查', tone: 'orange' as const },
  { key: 'paper', label: '模拟盘', tone: 'green' as const },
  { key: 'live', label: '实盘', tone: 'red' as const },
  { key: 'monitor', label: '监控', tone: 'cyan' as const },
  { key: 'archived', label: '归档', tone: 'gray' as const },
]

export default function StrategyLifecycle({ strategyId }: StrategyLifecycleProps) {
  const data = useStrategy()
  const [expanded, setExpanded] = useState(false)

  // Find the strategy's current stage from pipelineBoard
  const currentStage = useMemo(() => {
    if (!strategyId) return null
    for (const lane of data.pipelineBoard) {
      const ticket = lane.tickets.find((t) => t.id === strategyId)
      if (ticket) {
        // Map lane name to lifecycle key
        const laneKey = lane.lane.toLowerCase()
        if (laneKey.includes('draft')) return 'draft'
        if (laneKey.includes('research')) return 'research'
        if (laneKey.includes('backtest')) return 'backtest'
        if (laneKey.includes('risk')) return 'risk_review'
        if (laneKey.includes('paper')) return 'paper'
        if (laneKey.includes('live')) return 'live'
        if (laneKey.includes('monitor')) return 'monitor'
        if (laneKey.includes('archive')) return 'archived'
        return 'draft'
      }
    }
    // Fallback: try to find in matrix
    const matrixRow = data.matrix.find((m) => m.id === strategyId)
    if (matrixRow) {
      const status = matrixRow.status
      if (status === 'draft') return 'draft'
      if (status === 'backtest' || (status as string) === 'backtesting') return 'backtest'
      if (status === 'paper') return 'paper'
      if (status === 'live') return 'live'
      if (status === 'paused') return 'monitor'
    }
    return null
  }, [strategyId, data.pipelineBoard, data.matrix])

  const currentIndex = currentStage
    ? LIFECYCLE_STAGES.findIndex((s) => s.key === currentStage)
    : -1

  return (
    <div className="strategy-lifecycle">
      <button className="lifecycle-toggle" onClick={() => setExpanded((v) => !v)}>
        <span className="lifecycle-toggle-icon">{expanded ? '▼' : '▶'}</span>
        <div className="lifecycle-toggle-text">
          <strong>策略生命周期</strong>
          <span>
            {strategyId
              ? currentStage
                ? `当前阶段：${LIFECYCLE_STAGES.find((s) => s.key === currentStage)?.label || currentStage}`
                : '选择一个策略查看生命周期'
              : '从策略矩阵中选择一个策略查看其生命周期'}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="lifecycle-flow">
          <div className="lifecycle-track">
            {LIFECYCLE_STAGES.map((stage, i) => {
              const isCurrent = i === currentIndex
              const isPast = currentIndex >= 0 && i < currentIndex
              const isFuture = currentIndex >= 0 && i > currentIndex
              return (
                <div
                  key={stage.key}
                  className={`lifecycle-stage ${isCurrent ? 'current' : ''} ${isPast ? 'past' : ''} ${isFuture ? 'future' : ''}`}
                >
                  <div className={`lifecycle-stage-dot dot-${stage.tone}`}>
                    {isPast && '✓'}
                    {isCurrent && '●'}
                  </div>
                  <span className="lifecycle-stage-label">{stage.label}</span>
                  {isCurrent && (
                    <span className="lifecycle-stage-badge">当前</span>
                  )}
                </div>
              )
            })}
          </div>

          {strategyId && currentStage && (
            <div className="lifecycle-next-actions">
              <span className="lifecycle-next-label">下一步操作</span>
              <div className="lifecycle-next-buttons">
                {currentStage === 'draft' && (
                  <>
                    <button className="btn">开始研究</button>
                    <button className="btn secondary">编辑草稿</button>
                  </>
                )}
                {currentStage === 'research' && (
                  <>
                    <button className="btn">运行回测</button>
                    <button className="btn secondary">优化信号</button>
                  </>
                )}
                {currentStage === 'backtest' && (
                  <>
                    <button className="btn">提交风控审查</button>
                    <button className="btn secondary">查看回测报告</button>
                  </>
                )}
                {currentStage === 'risk_review' && (
                  <>
                    <button className="btn">批准模拟盘</button>
                    <button className="btn danger">驳回</button>
                  </>
                )}
                {currentStage === 'paper' && (
                  <>
                    <button className="btn">推送到实盘</button>
                    <button className="btn secondary">查看模拟表现</button>
                  </>
                )}
                {currentStage === 'live' && (
                  <>
                    <button className="btn secondary">查看实盘监控</button>
                    <button className="btn danger">暂停策略</button>
                  </>
                )}
                {currentStage === 'monitor' && (
                  <>
                    <button className="btn secondary">查看监控</button>
                    <button className="btn">恢复</button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
