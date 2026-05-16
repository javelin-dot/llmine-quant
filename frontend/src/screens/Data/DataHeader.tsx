import { useData } from '../../contexts/DataContext'

interface Props {
  onModal?: (target: string) => void
}

const TIER_ICON: Record<string, string> = {
  research: '◇',
  paper: '◈',
  live: '◆',
}

export default function DataHeader({ onModal }: Props) {
  const data = useData()
  const h = data.header
  const tiers = data.tiers
  const kpis = data.kpis
  const libBits =
    h.totalBars != null && h.totalSymbols != null
      ? `${h.totalSymbols.toLocaleString()} 标的 · ${h.totalBars.toLocaleString()} bars`
      : null
  const featBits = h.featureCount != null && h.featureCount > 0 ? `${h.featureCount} 特征` : null

  // SVG gauge math (radius 52, stroke 9)
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const dash = (h.healthScore / 100) * circumference
  const gap = circumference - dash

  return (
    <header className="data-header">
      <div className="dh-body">
        {/* Top: title + status summary + badge */}
        <div className="dh-topbar">
          <div className="dh-title-group">
            <h3>数据可靠性中心</h3>
            <h4>Data Operations</h4>
          </div>
          <p className="dh-status-line">
            {h.totalSources} 总源 · {h.activeSources} 活跃
            {h.erroredSources > 0 && <em> · {h.erroredSources} 异常</em>}
            {libBits != null && <em> · {libBits}</em>}
            {featBits != null && <em> · {featBits}</em>}
            {h.latestTradeDate != null && h.latestTradeDate !== '' && (
              <em> · 最新 {h.latestTradeDate}</em>
            )}
          </p>
          <span className={`dh-badge tone-${h.healthStatusTone}`}>
            {h.healthStatus} · {h.healthScore}
          </span>
        </div>

        {/* Three column main content */}
        <div className="dh-columns">
          {/* Left: Health gauge */}
          <div className="dh-col dh-col-gauge">
            <div className="dh-gauge-wrap">
              <svg viewBox="0 0 140 140" width="100" height="100" aria-hidden="true">
                <defs>
                  <linearGradient id="dh-grad-green" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#3dd68c" />
                    <stop offset="100%" stopColor="#0fb46a" />
                  </linearGradient>
                  <linearGradient id="dh-grad-yellow" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#f9c74f" />
                    <stop offset="100%" stopColor="#e8a319" />
                  </linearGradient>
                  <linearGradient id="dh-grad-red" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#ff7a85" />
                    <stop offset="100%" stopColor="#e23952" />
                  </linearGradient>
                  <linearGradient id="dh-grad-blue" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#7cc6ff" />
                    <stop offset="100%" stopColor="#3a8de8" />
                  </linearGradient>
                </defs>
                <circle cx="70" cy="70" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="9" />
                <circle
                  cx="70"
                  cy="70"
                  r={radius}
                  fill="none"
                  stroke={`url(#dh-grad-${h.healthStatusTone})`}
                  strokeWidth="9"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${gap}`}
                  transform="rotate(-90 70 70)"
                />
              </svg>
              <div className="dh-gauge-text">
                <strong>{h.healthScore}</strong>
              </div>
            </div>
            <span className={`dh-gauge-status tone-${h.healthStatusTone}`}>{h.healthStatus}</span>
          </div>

          {/* Middle: Metrics */}
          <div className="dh-col dh-col-metrics">
            <div className="dh-metrics-grid">
              <div className="dh-metric">
                <small>P95 延迟</small>
                <strong>{h.p95LatencyMs}<em>ms</em></strong>
              </div>
              <div className="dh-metric">
                <small>缺失率</small>
                <strong>{(h.missingRate * 100).toFixed(2)}<em>%</em></strong>
              </div>
              <div className="dh-metric warn">
                <small>24H 事件</small>
                <strong>{h.incidents24h}</strong>
              </div>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="dh-col dh-col-actions">
            <button className="dh-btn ghost" onClick={() => onModal?.('global')}>查看血缘</button>
            <button className="dh-btn primary" onClick={() => onModal?.('approve')}>新增数据源</button>
          </div>
        </div>
      </div>

      {/* Tiers: horizontally scrollable */}
      <div className="dh-tiers-scroll">
        {tiers.map((t) => (
          <div className={`dh-tier tone-${t.tone}`} key={t.tier}>
            <div className="dh-tier-head">
              <span className="dh-tier-icon">{TIER_ICON[t.tier]}</span>
              <div className="dh-tier-title">
                <strong>{t.label}</strong>
                <em>{t.license}</em>
              </div>
              <div className="dh-tier-count">
                <strong>{t.count}</strong>
                <small>{t.active}/{t.count} active</small>
              </div>
            </div>
            <div className="dh-tier-foot">
              <code>{t.avgLatencyMs}ms</code>
              <p>{t.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="dh-kpi-strip">
        {kpis.map((k, i) => (
          <div className={`dh-kpi tone-${k.tone}`} key={i}>
            <small>{k.label}</small>
            <strong>{k.value}</strong>
            <em>{k.trend}</em>
          </div>
        ))}
      </div>
    </header>
  )
}
