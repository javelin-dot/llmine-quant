import { useState } from 'react'
import { useData } from '../../contexts/DataContext'

const TIER_LABEL: Record<string, string> = {
  research: 'RESEARCH',
  paper: 'PAPER',
  live: 'LIVE',
}

const STATUS_LABEL: Record<string, string> = {
  healthy: '健康',
  warning: '注意',
  error: '异常',
  maintenance: '维护',
}

type TierFilter = 'all' | 'research' | 'paper' | 'live'

export default function SourceMatrix() {
  const data = useData()
  const [filter, setFilter] = useState<TierFilter>('all')
  const all = data.sources
  const list = filter === 'all' ? all : all.filter((s) => s.tier === filter)

  const counts = all.reduce((acc, s) => {
    acc[s.tier] = (acc[s.tier] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="data-source-matrix">
      <div className="dsm-head">
        <div>
          <h4 className="dsm-title">数据源全景 · Source Matrix</h4>
          <span className="dsm-sub">14 个数据源 · 三层 license · 实时状态</span>
        </div>
        <div className="dsm-filter">
          <button className={filter === 'all' ? 'dsm-tab active' : 'dsm-tab'} onClick={() => setFilter('all')}>
            全部 <em>{all.length}</em>
          </button>
          <button className={filter === 'research' ? 'dsm-tab active tone-blue' : 'dsm-tab tone-blue'} onClick={() => setFilter('research')}>
            研究 <em>{counts.research || 0}</em>
          </button>
          <button className={filter === 'paper' ? 'dsm-tab active tone-yellow' : 'dsm-tab tone-yellow'} onClick={() => setFilter('paper')}>
            模拟 <em>{counts.paper || 0}</em>
          </button>
          <button className={filter === 'live' ? 'dsm-tab active tone-red' : 'dsm-tab tone-red'} onClick={() => setFilter('live')}>
            实盘 <em>{counts.live || 0}</em>
          </button>
        </div>
      </div>

      <div className="dsm-table-wrap">
        <table className="dsm-table">
          <thead>
            <tr>
              <th>数据源</th>
              <th>类型</th>
              <th>覆盖</th>
              <th>延迟 P50</th>
              <th>P95</th>
              <th>缺失</th>
              <th>漂移</th>
              <th>许可</th>
              <th>状态</th>
              <th>更新</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => {
              const slaWarn = s.latencyP95 > 80 && s.tier !== 'research'
              return (
                <tr className={`dsm-row tier-${s.tier} status-${s.statusTone}`} key={s.id}>
                  <td>
                    <div className="dsm-name">
                      <strong>{s.name}</strong>
                      <em>{s.provider}</em>
                    </div>
                  </td>
                  <td><span className="dsm-type">{s.type}</span></td>
                  <td><span className="dsm-coverage">{s.coverage}</span></td>
                  <td><code className="dsm-latency">{s.latencyMs}ms</code></td>
                  <td><code className={slaWarn ? 'dsm-latency warn' : 'dsm-latency'}>{s.latencyP95}ms</code></td>
                  <td>
                    <span className={s.missingPct >= 0.1 ? 'dsm-missing warn' : 'dsm-missing'}>
                      {s.missingPct.toFixed(2)}%
                    </span>
                  </td>
                  <td>
                    <div className="dsm-drift">
                      <span className="dsm-drift-bar"><i style={{ width: `${Math.min(s.driftScore, 100)}%` }} /></span>
                      <em>{s.driftScore}</em>
                    </div>
                  </td>
                  <td><span className={`dsm-license tone-${s.tierTone}`}>{TIER_LABEL[s.tier]}</span></td>
                  <td>
                    <span className={`dsm-status tone-${s.statusTone}`}>
                      <i />
                      {STATUS_LABEL[s.status]}
                    </span>
                  </td>
                  <td><code className="dsm-time">{s.lastUpdate}</code></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
