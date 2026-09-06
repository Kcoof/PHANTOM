import { api } from './api'
import type { AiStatus, ChatMessage } from '../types/ai'

interface SseCallbacks {
  onDelta: (text: string) => void
  onError?: (message: string) => void
  onDone?: () => void
}

async function consumeSse(url: string, body: unknown, cb: SseCallbacks): Promise<void> {
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (err) {
    cb.onError?.(err instanceof Error ? err.message : String(err))
    return
  }
  if (!response.ok || !response.body) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json()
      if (data?.detail) detail = data.detail
    } catch {
      /* keep status detail */
    }
    cb.onError?.(detail)
    return
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      const line = frame.trim()
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6)
      if (payload === '[DONE]') {
        cb.onDone?.()
        return
      }
      try {
        const parsed = JSON.parse(payload)
        if (parsed.delta) cb.onDelta(parsed.delta)
        if (parsed.error) cb.onError?.(parsed.error)
      } catch {
        /* skip malformed frame */
      }
    }
  }
  cb.onDone?.()
}

export const aiService = {
  async status(): Promise<AiStatus> {
    const { data } = await api.get<AiStatus>('/ai/status')
    return data
  },
  async conversations(): Promise<ChatMessage[]> {
    const { data } = await api.get<ChatMessage[]>('/ai/conversations')
    return data
  },
  streamChat(body: { message: string; context_type?: string; context_id?: number }, cb: SseCallbacks): Promise<void> {
    return consumeSse('/api/ai/chat', body, cb)
  },
  streamAnalyze(historyId: number, cb: SseCallbacks): Promise<void> {
    return consumeSse(`/api/ai/analyze-request/${historyId}`, {}, cb)
  },
  streamPayloads(body: { url: string; parameter: string; vuln_type: string; context?: string }, cb: SseCallbacks): Promise<void> {
    return consumeSse('/api/ai/suggest-payloads', body, cb)
  },
}
