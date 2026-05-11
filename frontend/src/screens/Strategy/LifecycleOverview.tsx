import { useStrategy } from '../../contexts/StrategyContext'

interface LifecycleOverviewProps {
  onFilterStage?: (stage: string | null) => void
  activeFilter?: string | null
}

const STAGE_META: {
  key: string
  label: string
  tone: 'blue' | 'green' | 'yellow' | 'purple' | 'red' | 'gray'
  emptyText: string
  context: string
}[] = [
  {
    key: 'ideas',
    label: '构思',
    tone: 'blue',
    emptyText: '暂无策略构思',
    context: '研究假设与策略概念',
  },
  {
    key: 'research',
    label: '研究',
    tone: 'purple',
    emptyText: '无进行中的研究',
    context: '信号分析与因子验证',
  },
  {
    key: 'backtest',
    label: '回测',
    tone: 'yellow',
    emptyText: '今日无回测运行',
    context: '历史模拟与样本外检验',
  },
  {
    key: 'paper',
    label: '模拟盘',
    tone: 'green',
    emptyText: '无活跃模拟策略',
    context: '实时市场模拟，无资金风险',
  },
  {
    key: 'live',
    label: '实盘',
    tone: 'red',
    emptyText: '无实盘部署',
    context: '真实资金生产交易',
  },
  {
    key: 'paused',
    label: '暂停 / 风控熔断',
    tone: 'gray',
    emptyText: '无暂停策略',
    context: '手动暂停或风控熔断',
  },
]

export default function LifecycleOverview({ onFilterStage, activeFilter }: LifecycleOverviewProps) {
  const data = useStrategy()

  const counts: Record<string, number> = {}
  STAGE_META.forEach((s) => { counts[s.key] = 0 })
  data.pipelineStatus.forEach((p) => {
    const key = p.stage.toLowerCase()
    if (key in counts) counts[key] = p.count
  })

  const total = Object.values(counts).reduce((a, b) => a + b, 0)

  return (
    <div className="lifecycle-overview">
      <div className="lifecycle-overview-head">
        <div>
          <h3 className="lifecycle-overview-title">策略生命周期</h3>
          <span className="lifecycle-overview-sub">
            共 {total} 个策略 &middot; 点击阶段卡片筛选下方列表
          </span>
        </div>
        {activeFilter && (
          <button className="lifecycle-clear-filter" onClick={() => onFilterStage?.(null)}>
            清除筛选 &#10005;
          </button>
        )}
      </div>
      <div className="lifecycle-cards">
        {STAGE_META.map((s) => {
          const count = counts[s.key] || 0
          const isActive = activeFilter === s.key
          return (
            <button
              key={s.key}
              className={`lifecycle-card card-${s.tone} ${isActive ? 'active' : ''}`}
              onClick={() => onFilterStage?.(isActive ? null : s.key)}
            >
              <div className="lifecycle-card-top">
                <span className={`lifecycle-dot dot-${s.tone}`} />
                <span className="lifecycle-card-label">{s.label}</span>
              </div>
              <div className="lifecycle-card-body">
                {count > 0 ? (
                  <>
                    <strong className="lifecycle-card-count">{count}</strong>
                    <span className="lifecycle-card-unit">
                      {count === 1 ? 'strategy' : 'strategies'}
                    </span>
                  </>
                ) : (
                  <span className="lifecycle-card-empty">{s.emptyText}</span>
                )}
              </div>
              <div className="lifecycle-card-context">{s.context}</div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
