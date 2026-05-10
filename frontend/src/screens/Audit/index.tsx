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
  return (
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
  )
}
