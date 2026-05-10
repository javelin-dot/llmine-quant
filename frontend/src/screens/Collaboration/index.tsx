import CollaborationHeader from './CollaborationHeader'
import ActiveReviews from './ActiveReviews'
import VersionDiff from './VersionDiff'
import ReviewThread from './ReviewThread'
import ABTestGrid from './ABTestGrid'
import ApprovalFlow from './ApprovalFlow'
import FooterCards from './FooterCards'

interface CollaborationProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Collaboration({ onModal }: CollaborationProps) {
  return (
    <div className="collab-root">
      <CollaborationHeader onModal={onModal} />
      <div className="collab-main">
        <ActiveReviews />
        <VersionDiff />
      </div>
      <div className="collab-sub">
        <ReviewThread />
        <ABTestGrid />
      </div>
      <ApprovalFlow />
      <FooterCards />
    </div>
  )
}
