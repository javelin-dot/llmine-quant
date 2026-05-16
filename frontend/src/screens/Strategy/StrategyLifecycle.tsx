import { useState, useMemo } from 'react'
import { api } from '../../lib/api'
import { useStrategy } from '../../contexts/StrategyContext'

interface StrategyLifecycleProps {
  strategyId?: string | null
  onNavigate?: (target: string) => void
  onChanged?: () => void
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

export default function StrategyLifecycle({ strategyId, onNavigate, onChanged }: StrategyLifecycleProps) {
  const data = useStrategy()
  const [expanded, setExpanded] = useState(true)
  const [saving, setSaving] = useState(false)

  const advance = async (newStatus: string) => {
    if (!strategyId || saving) return
    setSaving(true)
    try {
      await api.strategy.update(strategyId, { status: newStatus })
      onChanged?.()
    } catch (e) {
      console.error('lifecycle advance failed', e)
    } finally {
      setSaving(false)
    }
  }

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

  if (!strategyId) return null

  return (
    <div className="strategy-lifecycle">
      <button className="lifecycle-toggle" onClick={() => setExpanded((v) => !v)}>
        <span className="lifecycle-toggle-icon">{expanded ? '▼' : '▶'}</span>
        <div className="lifecycle-toggle-text">
          <strong>单策略推进状态</strong>
          <span>
            {currentStage
              ? `当前阶段：${LIFECYCLE_STAGES.find((s) => s.key === currentStage)?.label || currentStage}`
              : '当前策略暂无推进阶段记录'}
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
                    <button className="btn" disabled={saving} onClick={() => void advance('research')}>
                      {saving ? '处理中…' : '开始研究'}
                    </button>
                  </>
                )}
                {currentStage === 'research' && (
                  <>
                    <button className="btn" disabled={saving} onClick={() => {
                      onNavigate?.(`backtest:strategyId=${encodeURIComponent(strategyId)}`)
                    }}>
                      运行回测
                    </button>
                  </>
                )}
                {currentStage === 'backtest' && (
                  <>
                    <button className="btn" disabled={saving} onClick={() => void advance('risk_review')}>
                      {saving ? '处理中…' : '提交风控审查'}
                    </button>
                    <button className="btn secondary" onClick={() => {
                      onNavigate?.(`backtest:strategyId=${encodeURIComponent(strategyId)}`)
                    }}>
                      查看回测报告
                    </button>
                  </>
                )}
                {currentStage === 'risk_review' && (
                  <>
                    <button className="btn" disabled={saving} onClick={async () => {
                      await advance('paper')
                      onNavigate?.('paper')
                    }}>
                      {saving ? '处理中…' : '批准→模拟盘'}
                    </button>
                    <button className="btn danger" disabled={saving} onClick={() => void advance('research')}>
                      驳回
                    </button>
                  </>
                )}
                {currentStage === 'paper' && (
                  <>
                    <button className="btn" disabled={saving} onClick={async () => {
                      await advance('live')
                      onNavigate?.('execution')
                    }}>
                      {saving ? '处理中…' : '推送到实盘'}
                    </button>
                    <button className="btn secondary" onClick={() => onNavigate?.('paper')}>
                      查看模拟表现
                    </button>
                  </>
                )}
                {currentStage === 'live' && (
                  <>
                    <button className="btn secondary" onClick={() => onNavigate?.('execution')}>
                      查看实盘审批
                    </button>
                    <button className="btn danger" disabled={saving} onClick={() => void advance('paused')}>
                      {saving ? '处理中…' : '暂停策略'}
                    </button>
                  </>
                )}
                {currentStage === 'monitor' && (
                  <>
                    <button className="btn secondary" onClick={() => onNavigate?.('execution')}>
                      查看监控
                    </button>
                    <button className="btn" disabled={saving} onClick={() => void advance('live')}>
                      {saving ? '处理中…' : '恢复'}
                    </button>
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
