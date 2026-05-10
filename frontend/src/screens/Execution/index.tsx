import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { ExecutionProvider } from '../../contexts/ExecutionContext'
import ApprovalStrip from './ApprovalStrip'
import ApprovalQueue from './ApprovalQueue'
import PreTradeChecks from './PreTradeChecks'
import OrderBook from './OrderBook'
import ExecutionMetrics from './ExecutionMetrics'
import AgentTrace from './AgentTrace'

interface ExecutionProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Execution({ onModal }: ExecutionProps) {
  const [data, setData] = useState<MockData['execution'] | null>(null)

  useEffect(() => {
    api.execution.overview()
      .then(setData)
      .catch((e) => console.error('Execution API error:', e))
  }, [])

  if (!data) return <div className="execution-root">Loading Execution…</div>

  return (
    <ExecutionProvider value={data}>
      <div className="execution-root">
        <ApprovalStrip />
        <div className="execution-main">
          <ApprovalQueue onModal={onModal} />
          <PreTradeChecks />
        </div>
        <OrderBook />
        <div className="execution-sub">
          <ExecutionMetrics />
          <AgentTrace />
        </div>
      </div>
    </ExecutionProvider>
  )
}
