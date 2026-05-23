type MessageHandler = (msg: any) => void

const RECONNECT_DELAY = 3000

function getWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

let ws: WebSocket | null = null
let handler: MessageHandler | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let shouldReconnect = false

export function connect(onMessage: MessageHandler): void {
  handler = onMessage
  shouldReconnect = true
  _connect()
}

function _connect(): void {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  ws = new WebSocket(getWsUrl())

  ws.onopen = () => {
    console.log('[WS] connected')
    const current = ws!
    const ping = setInterval(() => {
      if (current.readyState === WebSocket.OPEN) current.send('ping')
    }, 30000)
    current.addEventListener('close', () => clearInterval(ping), { once: true })
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type !== 'pong' && handler) {
        handler(msg)
      }
    } catch {
      // ignore malformed messages
    }
  }

  ws.onclose = () => {
    console.log('[WS] disconnected')
    ws = null
    if (shouldReconnect && reconnectTimer === null) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        _connect()
      }, RECONNECT_DELAY)
    }
  }

  ws.onerror = () => {
    ws?.close()
  }
}

export function disconnect(): void {
  shouldReconnect = false
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  ws?.close()
  ws = null
}
