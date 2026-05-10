import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { AuditProvider } from '../../contexts/AuditContext'
import AuditHeader from './AuditHeader'
import AuditLog from './AuditLog'
import ActorBreakdown from './ActorBreakdown'
import ToolRegistry from './ToolRegistry'
import HITLRules from './HITLRules'

interface AuditProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Audit({ onModal }: AuditProps) {
  const [data, setData] = useState<MockData['audit'] | null>(null)

  useEffect(() => {
    api.audit.overview()
      .then(setData)
      .catch((e) => console.error('Audit API error:', e))
  }, [])

  if (!data) return <div className="audit-root">Loading Audit…</div>

  return (
    <AuditProvider value={data}>
      <div className="audit-root">
        <AuditHeader onModal={onModal} />
        <AuditLog />
        <div className="audit-sub">
          <ActorBreakdown />
          <div className="audit-side">
            <ToolRegistry />
            <HITLRules />
          </div>
        </div>
      </div>
    </AuditProvider>
  )
}
