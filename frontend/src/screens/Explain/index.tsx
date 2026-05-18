import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { ExplainProvider } from '../../contexts/ExplainContext'
import SignalHeader from './SignalHeader'
import AttributionWaterfall from './AttributionWaterfall'
import ConfidenceRadar from './ConfidenceRadar'
import DecisionChain from './DecisionChain'
import LineageGraph from './LineageGraph'
import BiasGate from './BiasGate'
import SimilarHistory from './SimilarHistory'

function downloadExplainJson(payload: MockData['explain']) {
  const name = `explain-${payload.signalHeader.traceId}.json`
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

interface ExplainProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Explain(_props: ExplainProps) {
  const [data, setData] = useState<MockData['explain'] | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setFetchError(null)
    try {
      const d = await api.explain.overview()
      setData(d)
    } catch (e) {
      setData(null)
      setFetchError(
        e instanceof Error ? e.message : 'Explain 数据加载失败（需后端迁移 + 种子入库，禁止前端 mock）。',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const showToast = useCallback((t: { type: 'ok' | 'err'; text: string }) => {
    setToast(t)
    window.setTimeout(() => setToast(null), 4200)
  }, [])

  const handleApproveConfirm = async () => {
    if (!data?.signalHeader.traceId?.trim()) return
    setBusy(true)
    setConfirmOpen(false)
    try {
      await api.explain.approveSignal(data.signalHeader.traceId)
      await load()
      showToast({ type: 'ok', text: '审批已记录，页头状态与决策链已更新。' })
    } catch (e) {
      const msg =
        e instanceof Error
          ? e.message
          : '审批请求失败（需连接后端 /api/v1/explain/signal/approve）'
      showToast({ type: 'err', text: msg })
    } finally {
      setBusy(false)
    }
  }

  if (loading && data === null) {
    return <div className="explain-root explain-loading">加载 Explain…</div>
  }

  if (fetchError !== null) {
    return (
      <div className="explain-root explain-fetch-error">
        <h3>Explain 不可用</h3>
        <p>{fetchError}</p>
        <button type="button" className="btn" onClick={() => void load()}>
          重试
        </button>
        <p className="explain-fetch-hint">请确认后端已启动且已完成数据库迁移。</p>
      </div>
    )
  }

  if (data === null) return null

  const hdr = data.signalHeader
  const hasPersistedSignal = Boolean(hdr.traceId?.trim())
  const canApprove = hasPersistedSignal && hdr.status !== '已批准'

  return (
    <ExplainProvider value={data}>
      {toast !== null ? (
        <div className={`explain-toast ${toast.type}`} role="status">
          {toast.text}
        </div>
      ) : null}

      {confirmOpen ? (
        <div
          className="modal-backdrop show explain-approve-layer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="explain-approve-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setConfirmOpen(false)
          }}
        >
          <div className="modal explain-approve-dialog">
            <div className="modal-body">
              <h3 id="explain-approve-title">审批该信号 trace</h3>
              <p>
                Trace <code className="explain-approve-code">{hdr.traceId}</code> · {hdr.target} ·{' '}
                <strong>{hdr.strategy}</strong>
                <br />
                批准后状态将变更为「已批准」，决策链最后一步同步为放行说明。
              </p>
            </div>
            <div className="modal-actions">
              <button type="button" className="btn secondary" onClick={() => setConfirmOpen(false)}>
                取消
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => void handleApproveConfirm()}
              >
                {busy ? '处理中…' : '确认批准'}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="explain-root">
        {!hasPersistedSignal ? (
          <div className="bt-empty-line" style={{ marginBottom: '0.75rem' }}>
            当前没有持久化的信号解释记录；策略产出 Explain 条目后将在此展示。
          </div>
        ) : null}
        <SignalHeader
          canApprove={canApprove}
          busy={busy}
          onRequestApprove={() => setConfirmOpen(true)}
          onExport={() => {
            downloadExplainJson(data)
            showToast({ type: 'ok', text: '已导出当前解释快照（JSON）。' })
          }}
        />
        <div className="explain-main">
          <AttributionWaterfall />
          <ConfidenceRadar />
        </div>
        <DecisionChain />
        <LineageGraph />
        <div className="explain-sub">
          <BiasGate />
          <SimilarHistory />
        </div>
      </div>
    </ExplainProvider>
  )
}
