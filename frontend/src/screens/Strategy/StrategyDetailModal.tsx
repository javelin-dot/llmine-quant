import { useEffect, useMemo, useState } from 'react'
import { api, type StrategyDetail, type StrategyUpdatePayload } from '../../lib/api'

interface StrategyDetailModalProps {
  strategyId: string
  onClose: () => void
  onChanged?: () => void
}

const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿', tone: 'gray' },
  { value: 'research', label: '研究中', tone: 'blue' },
  { value: 'backtesting', label: '回测中', tone: 'purple' },
  { value: 'backtest', label: 'Backtest', tone: 'blue' },
  { value: 'paper', label: '模拟盘', tone: 'yellow' },
  { value: 'live', label: '实盘', tone: 'green' },
  { value: 'paused', label: '暂停', tone: 'purple' },
  { value: 'archived', label: '归档', tone: 'gray' },
]

const FAMILY_OPTIONS = ['trend', 'mean_reversion', 'value', 'quality', 'momentum', 'arbitrage', 'event']
const RISK_OPTIONS = [
  { value: 'conservative', label: '保守' },
  { value: 'balanced', label: '平衡' },
  { value: 'aggressive', label: '激进' },
]
const MARKET_OPTIONS = ['A', 'US', 'HK', 'crypto']
const FREQUENCY_OPTIONS = ['1m', '5m', '15m', '1h', '1d', '1w']

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined) return '—'
  return `${(v * 100).toFixed(digits)}%`
}
function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return '—'
  return v.toFixed(digits)
}
function fmtTime(iso: string): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

export default function StrategyDetailModal({ strategyId, onClose, onChanged }: StrategyDetailModalProps) {
  const [detail, setDetail] = useState<StrategyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<StrategyUpdatePayload>({})
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [tab, setTab] = useState<'overview' | 'code' | 'events'>('overview')

  useEffect(() => {
    let alive = true
    api.strategy.detail(strategyId)
      .then((d) => {
        if (!alive) return
        setDetail(d)
        setForm({
          name: d.name,
          family: d.family,
          description: d.description ?? '',
          riskProfile: d.riskProfile,
          market: d.market,
          universe: d.universe ?? '',
          frequency: d.frequency,
          status: d.status,
        })
      })
      .catch((e) => { if (alive) setError(String(e)) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [strategyId])

  const statusMeta = useMemo(
    () => STATUS_OPTIONS.find((o) => o.value === (detail?.status ?? '')) ?? { label: detail?.status ?? '—', tone: 'gray' },
    [detail?.status]
  )

  const codeText = detail?.versions?.[0]?.codeText ?? null

  const handleSave = async () => {
    if (!detail) return
    setSaving(true)
    setError(null)
    try {
      const updated = await api.strategy.update(detail.id, {
        ...form,
        // Send empty strings as null for nullable fields
        description: form.description === '' ? null : form.description,
        universe: form.universe === '' ? null : form.universe,
      })
      setDetail(updated)
      setEditing(false)
      onChanged?.()
    } catch (e) {
      setError(String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!detail) return
    setDeleting(true)
    try {
      await api.strategy.delete(detail.id)
      onChanged?.()
      onClose()
    } catch (e) {
      setError(String(e))
      setDeleting(false)
    }
  }

  return (
    <div
      className="modal-backdrop show"
      role="dialog"
      aria-modal="true"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="strategy-detail-modal">
        <header className="sd-head">
          <div className="sd-head-main">
            <span className={`sd-status status-tag-${statusMeta.tone}`}>
              <span className={`status-dot-mini status-dot-${statusMeta.tone}`} />
              {statusMeta.label}
            </span>
            {editing ? (
              <input
                className="sd-name-input"
                value={form.name ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="策略名称"
              />
            ) : (
              <h3 className="sd-name">{detail?.name ?? '加载中…'}</h3>
            )}
            <span className="sd-id">#{strategyId.slice(0, 8)}</span>
          </div>
          <div className="sd-head-actions">
            {!editing && detail && (
              <>
                <button className="btn secondary sd-btn" onClick={() => setEditing(true)}>编辑</button>
                <button className="btn danger sd-btn" onClick={() => setConfirmDelete(true)}>删除</button>
              </>
            )}
            <button className="sd-close" onClick={onClose} aria-label="关闭">×</button>
          </div>
        </header>

        {loading && <div className="sd-loading">加载策略详情…</div>}
        {error && !loading && (
          <div className="sd-error">⚠ {error}</div>
        )}

        {detail && !loading && (
          <>
            <nav className="sd-tabs" aria-label="详情分类">
              <button className={tab === 'overview' ? 'sd-tab active' : 'sd-tab'} onClick={() => setTab('overview')}>
                概览
              </button>
              <button className={tab === 'code' ? 'sd-tab active' : 'sd-tab'} onClick={() => setTab('code')}>
                代码 · v{detail.versions[0]?.version ?? '—'}
              </button>
              <button className={tab === 'events' ? 'sd-tab active' : 'sd-tab'} onClick={() => setTab('events')}>
                流水线 · {detail.recentEvents.length}
              </button>
            </nav>

            <div className="sd-body">
              {tab === 'overview' && (
                <div className="sd-overview">
                  {/* Metrics */}
                  <div className="sd-metrics">
                    <div className="sd-metric">
                      <small>年化收益</small>
                      <strong className={(detail.annualReturn ?? 0) >= 0 ? 'pos' : 'neg'}>
                        {fmtPct(detail.annualReturn)}
                      </strong>
                    </div>
                    <div className="sd-metric">
                      <small>最大回撤</small>
                      <strong className="neg">{fmtPct(detail.maxDd)}</strong>
                    </div>
                    <div className="sd-metric">
                      <small>夏普</small>
                      <strong>{fmtNum(detail.sharpe)}</strong>
                    </div>
                    <div className="sd-metric">
                      <small>OOS 分</small>
                      <strong>{fmtNum(detail.oosScore)}</strong>
                    </div>
                  </div>

                  {/* Fields */}
                  <div className="sd-fields">
                    <div className="sd-field">
                      <small>族群</small>
                      {editing ? (
                        <select
                          value={form.family ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, family: e.target.value }))}
                        >
                          {FAMILY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <strong>{detail.family}</strong>
                      )}
                    </div>
                    <div className="sd-field">
                      <small>市场</small>
                      {editing ? (
                        <select
                          value={form.market ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
                        >
                          {MARKET_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <strong>{detail.market}</strong>
                      )}
                    </div>
                    <div className="sd-field">
                      <small>风险偏好</small>
                      {editing ? (
                        <select
                          value={form.riskProfile ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, riskProfile: e.target.value }))}
                        >
                          {RISK_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      ) : (
                        <strong>{RISK_OPTIONS.find((r) => r.value === detail.riskProfile)?.label ?? detail.riskProfile}</strong>
                      )}
                    </div>
                    <div className="sd-field">
                      <small>频率</small>
                      {editing ? (
                        <select
                          value={form.frequency ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value }))}
                        >
                          {FREQUENCY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <strong>{detail.frequency}</strong>
                      )}
                    </div>
                    <div className="sd-field">
                      <small>股票池</small>
                      {editing ? (
                        <input
                          value={form.universe ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, universe: e.target.value }))}
                          placeholder="例如 沪深300"
                        />
                      ) : (
                        <strong>{detail.universe ?? '—'}</strong>
                      )}
                    </div>
                    <div className="sd-field">
                      <small>状态</small>
                      {editing ? (
                        <select
                          value={form.status ?? ''}
                          onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                        >
                          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      ) : (
                        <strong>{statusMeta.label}</strong>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <div className="sd-desc">
                    <small>描述</small>
                    {editing ? (
                      <textarea
                        value={form.description ?? ''}
                        onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                        placeholder="策略简述"
                        rows={4}
                      />
                    ) : (
                      <p>{detail.description || '—'}</p>
                    )}
                  </div>

                  {/* Meta */}
                  <div className="sd-meta">
                    <span>创建于 {fmtTime(detail.createdAt)}</span>
                    <span>·</span>
                    <span>更新于 {fmtTime(detail.updatedAt)}</span>
                    {detail.ownerId && (
                      <>
                        <span>·</span>
                        <span>所有者 {detail.ownerId}</span>
                      </>
                    )}
                  </div>
                </div>
              )}

              {tab === 'code' && (
                <div className="sd-code">
                  {codeText ? (
                    <pre>{codeText}</pre>
                  ) : (
                    <div className="sd-empty">该策略暂无代码版本（可能仍在生成中）</div>
                  )}
                </div>
              )}

              {tab === 'events' && (
                <div className="sd-events">
                  {detail.recentEvents.length === 0 && <div className="sd-empty">暂无流水线事件</div>}
                  {detail.recentEvents.map((e) => (
                    <div className="sd-event" key={e.id}>
                      <span className="sd-event-time">{fmtTime(e.createdAt)}</span>
                      <span className="sd-event-stage">{e.stage}</span>
                      <span className="sd-event-name">{e.event}</span>
                      <span className="sd-event-progress">{e.progress}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <footer className="sd-foot">
              {editing ? (
                <>
                  <button className="btn secondary" disabled={saving} onClick={() => { setEditing(false); setForm({ ...form, name: detail.name }) }}>
                    取消
                  </button>
                  <button className="btn success" disabled={saving} onClick={handleSave}>
                    {saving ? '保存中…' : '保存修改'}
                  </button>
                </>
              ) : (
                <button className="btn secondary" onClick={onClose}>关闭</button>
              )}
            </footer>
          </>
        )}

        {confirmDelete && detail && (
          <div className="sd-confirm" role="alertdialog">
            <p>确认删除策略 <strong>{detail.name}</strong>？</p>
            <p className="sd-confirm-hint">删除后可联系管理员从审计日志恢复（软删除）。</p>
            <div className="sd-confirm-actions">
              <button className="btn secondary" onClick={() => setConfirmDelete(false)} disabled={deleting}>
                取消
              </button>
              <button className="btn danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? '删除中…' : '确认删除'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
