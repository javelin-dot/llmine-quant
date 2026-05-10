import { useEffect, useState } from 'react'
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

interface ExplainProps {
  onNavigate?: (target: string) => void
  onModal?: (target: string) => void
}

export default function Explain({ onModal }: ExplainProps) {
  const [data, setData] = useState<MockData['explain'] | null>(null)

  useEffect(() => {
    api.explain.overview()
      .then(setData)
      .catch((e) => console.error('Explain API error:', e))
  }, [])

  if (!data) return <div className="explain-root">Loading Explain…</div>

  return (
    <ExplainProvider value={data}>
      <div className="explain-root">
        <SignalHeader onModal={onModal} />
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
