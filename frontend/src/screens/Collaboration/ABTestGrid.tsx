import { useCollaboration } from '../../contexts/CollaborationContext'

const STATUS_LABEL: Record<string, string> = {
  running: '运行中',
  completed: '已完成',
  pending: '待启动',
}

function miniSparkline(points: number[]) {
  const w = 120
  const h = 32
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const step = w / (points.length - 1)
  const coords = points.map((v, i) => `${i * step},${h - ((v - min) / range) * h}`).join(' ')
  const area = `${coords} ${w},${h} 0,${h}`
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="cab-spark">
      <defs>
        <linearGradient id="cab-spark-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3dd68c" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#3dd68c" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#cab-spark-grad)" />
      <polyline points={coords} fill="none" stroke="#3dd68c" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

export default function ABTestGrid() {
  const data = useCollaboration()
  const tests = data.abTests

  return (
    <div className="collab-ab">
      <div className="cab-head">
        <div>
          <h4 className="cab-title">A/B 测试 · Experiment Grid</h4>
          <span className="cab-sub">{tests.length} 组对照 · 控制组 / 实验组 并行运行</span>
        </div>
      </div>
      <div className="cab-grid">
        {tests.map((t) => (
          <article className={`cab-card status-${t.statusTone}`} key={t.id}>
            <header className="cab-card-head">
              <div>
                <strong>{t.name}</strong>
                <span className="cab-meta">{t.control} vs {t.variant}</span>
              </div>
              <span className={`cab-status pill-${t.statusTone}`}>{STATUS_LABEL[t.status]}</span>
            </header>
            <div className="cab-stats">
              <div>
                <small>样本</small>
                <strong>{t.samples}</strong>
              </div>
              <div>
                <small>周期</small>
                <strong>{t.duration}</strong>
              </div>
              <div>
                <small>提升</small>
                <strong className={t.improvement >= 0 ? 'positive' : 'negative'}>
                  {t.improvement >= 0 ? '+' : ''}{(t.improvement * 100).toFixed(1)}%
                </strong>
              </div>
            </div>
            {miniSparkline(t.sparkline)}
          </article>
        ))}
      </div>
    </div>
  )
}
