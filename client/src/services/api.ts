import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
})

export default api

/** SSE 流式聊天 — 返回一个 AbortController 用于取消 */
export async function streamChat(
  npcId: string,
  text: string,
  onDelta: (delta: string) => void,
  onDone: (options: string[]) => void,
  onError: (err: string) => void,
): Promise<AbortController> {
  const controller = new AbortController()
  const base = import.meta.env.BASE_URL
  const url = `${base}api/chat/${npcId}/stream?message=${encodeURIComponent(text)}`

  try {
    const resp = await fetch(url, {
      method: 'POST',
      signal: controller.signal,
    })

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({ reply: `HTTP ${resp.status}` }))
      onError(errData.reply || `HTTP ${resp.status}`)
      return controller
    }

    const reader = resp.body?.getReader()
    if (!reader) {
      onError('无法读取响应流')
      return controller
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.delta) {
              onDelta(data.delta)
            } else if (data.done) {
              // 流结束，可能还有 options
            } else if (data.options !== undefined) {
              onDone(data.options)
            } else if (data.error) {
              onError(data.error)
            }
          } catch {
            // 忽略无法解析的行
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      onError(err.message || '网络错误')
    }
  }

  return controller
}
