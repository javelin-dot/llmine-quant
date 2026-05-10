import { useState } from 'react'
import { mock } from '../../data'

const RESULT_LABEL: Record<string, string> = {
  PASS: '通过',
  DENIED: '拒绝',
  BLOCKED: '阻断',
  APPROVAL: '待审批',
  APPROVED: '已批准',
  TRACE: '归因',
  VERIFIED: '已校验',
  AUTO: '自动',
  FILLED: '已成交',
  NOTIFY: '通知',
}

type TypeFilter = 'all' | 'human' | 'agent' | 'system'

export default function AuditLog() {
  const [filter, setFilter] = useState<TypeFilter>('all')
  const all = mock.audit.rows
  const list = filter === 'all' ? all : all.filter((r) => r.actorType === filter)

  const counts = all.reduce((acc, r) => {
    acc[r.actorType] = (acc[r.actorType] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="audit-log">
      <div className="al-head">
        <div>
          <h4 className="al-title">决策日志 · Decision Log</h4>
          <span className="al-sub">{all.length} 条记录 · 不可篡改 · 按时间倒序</span>
        </div>
        <div className="al-filter">
          <button className={filter === 'all' ? 'al-tab active' : 'al-tab'} onClick={() => setFilter('all')}>
            全部 <em>{all.length}</em>
          </button>
          <button className={filter === 'agent' ? 'al-tab active' : 'al-tab'} onClick={() => setFilter('agent')}>
            Agent <em>{counts.agent || 0}</em>
          </button>
          <button className={filter === 'human' ? 'al-tab active' : 'al-tab'} onClick={() => setFilter('human')}>
            人工 <em>{counts.human || 0}</em>
          </button>
          <button className={filter === 'system' ? 'al-tab active' : 'al-tab'} onClick={() => setFilter('system')}>
            系统 <em>{counts.system || 0}</em>
          </button>
        </div>
      </div>

      <div className="al-table-wrap">
        <table className="al-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>Actor</th>
              <th>动作</th>
              <th>资源</th>
              <th>结果</th>
              <th>置信度</th>
              <th>详情</th>
              <th>Trace ID</th>
            </tr>
          </thead>
          <tbody>
            {list.map((r, i) => (
              <tr className={`al-row tone-${r.resultTone}`} key={i}>
                <td><code className="al-time">{r.time}</code></td>
                <td>
                  <div className="al-actor">
                    <span className={`al-actor-type type-${r.actorType}`}>{r.actorType[0].toUpperCase()}</span>
                    <strong>{r.actor}</strong>
                  </div>
                </td>
                <td><span className="al-action">{r.action}</span></td>
                <td><code className="al-resource">{r.resource}</code></td>
                <td>
                  <span className={`al-result pill-${r.resultTone}`}>
                    {RESULT_LABEL[r.result] || r.result}
                  </span>
                </td>
                <td>
                  <span className={`al-confidence ${r.confidence >= 0.9 ? 'high' : r.confidence >= 0.8 ? 'mid' : 'low'}`}>
                    {r.confidence === 1.0 ? '1.00' : r.confidence.toFixed(2)}
                  </span>
                </td>
                <td><span className="al-detail">{r.detail}</span></td>
                <td><code className="al-trace">{r.traceId}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
