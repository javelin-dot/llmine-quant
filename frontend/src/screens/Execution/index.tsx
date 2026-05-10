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
  return (
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
  )
}
