import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { MockData } from '../../data/types'
import { CollaborationProvider } from '../../contexts/CollaborationContext'
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
  const [data, setData] = useState<MockData['collaboration'] | null>(null)

  useEffect(() => {
    api.collaboration.overview()
      .then(setData)
      .catch((e) => console.error('Collaboration API error:', e))
  }, [])

  if (!data) return <div className="collab-root">Loading Collaboration…</div>

  return (
    <CollaborationProvider value={data}>
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
    </CollaborationProvider>
  )
}
