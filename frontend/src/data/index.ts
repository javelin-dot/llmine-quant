import type { MockData } from './types'
import { cryptoMock } from './mock_crypto'
import { ashareMock } from './mock_ashare'

const market = import.meta.env.VITE_MARKET || 'ashare'

export const mock: MockData = market === 'crypto' ? cryptoMock : ashareMock
export const isCrypto = market === 'crypto'
export const isAshare = market === 'ashare'
