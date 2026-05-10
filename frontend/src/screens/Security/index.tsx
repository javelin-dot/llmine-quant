import SecurityHeader from './SecurityHeader'
import AccountSegments from './AccountSegments'
import VaultStatus from './VaultStatus'
import AIPermissionMatrix from './AIPermissionMatrix'
import WithdrawalGuard from './WithdrawalGuard'
import SecurityEvents from './SecurityEvents'

interface SecurityProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Security({ onModal }: SecurityProps) {
  return (
    <div className="security-root">
      <SecurityHeader onModal={onModal} />
      <div className="security-main">
        <AccountSegments />
        <VaultStatus />
      </div>
      <AIPermissionMatrix />
      <div className="security-sub">
        <WithdrawalGuard />
        <SecurityEvents />
      </div>
    </div>
  )
}
