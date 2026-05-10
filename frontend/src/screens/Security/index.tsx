import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { SecurityProvider } from '../../contexts/SecurityContext'
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
  const [data, setData] = useState<MockData['security'] | null>(null)

  useEffect(() => {
    api.security.overview()
      .then(setData)
      .catch((e) => console.error('Security API error:', e))
  }, [])

  if (!data) return <div className="security-root">Loading Security…</div>

  return (
    <SecurityProvider value={data}>
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
    </SecurityProvider>
  )
}
