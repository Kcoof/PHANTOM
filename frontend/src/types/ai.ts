export interface AiStatus {
  available: boolean
  provider: string
  model: string
  base_url: string
  detail: string | null
  models?: string[]
}

export interface ChatMessage {
  id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  context_type?: string | null
  context_id?: number | null
  model?: string | null
}
