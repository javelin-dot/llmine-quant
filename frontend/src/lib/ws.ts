/**
 * WebSocket client with auto-reconnect and topic subscriptions.
 *
 * Usage:
 *   const ws = createWsClient('strategy-events')
 *   ws.on('strategy_update', payload => console.log(payload))
 *   ws.connect()
 *   // ...
 *   ws.disconnect()
 */

export type WsHandler = (payload: Record<string, unknown>) => void

interface WsClient {
  connect: () => void
  disconnect: () => void
  on: (type: string, handler: WsHandler) => () => void
  isConnected: () => boolean
}

const WS_BASE = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${proto}//${host}/ws`
})()

export function createWsClient(topic: string): WsClient {
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let shouldReconnect = true
  let reconnectDelay = 1000
  const handlers = new Map<string, Set<WsHandler>>()

  function dispatch(msg: Record<string, unknown>) {
    const type = typeof msg.type === 'string' ? msg.type : '__all__'
    handlers.get(type)?.forEach(h => h(msg))
    handlers.get('*')?.forEach(h => h(msg))
  }

  function connect() {
    if (socket?.readyState === WebSocket.OPEN) return
    socket = new WebSocket(`${WS_BASE}/${topic}`)

    socket.onopen = () => {
      reconnectDelay = 1000
    }

    socket.onmessage = e => {
      try {
        const msg = JSON.parse(e.data) as Record<string, unknown>
        dispatch(msg)
      } catch {
        // ignore malformed frames
      }
    }

    socket.onclose = () => {
      if (!shouldReconnect) return
      reconnectTimer = setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 1.5, 30_000)
        connect()
      }, reconnectDelay)
    }

    socket.onerror = () => {
      socket?.close()
    }
  }

  function disconnect() {
    shouldReconnect = false
    if (reconnectTimer) clearTimeout(reconnectTimer)
    socket?.close()
    socket = null
  }

  function on(type: string, handler: WsHandler): () => void {
    if (!handlers.has(type)) handlers.set(type, new Set())
    handlers.get(type)!.add(handler)
    return () => handlers.get(type)?.delete(handler)
  }

  return {
    connect,
    disconnect,
    on,
    isConnected: () => socket?.readyState === WebSocket.OPEN,
  }
}

// Singleton clients for each topic
export const strategyWs = createWsClient('strategy-events')
export const executionWs = createWsClient('execution-events')
export const riskWs = createWsClient('risk-events')
