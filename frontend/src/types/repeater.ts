export interface RepeaterTab {
  id: number
  name: string
  timestamp?: string
  method: string
  url: string
  request_headers: Record<string, string>
  request_body: string | null
  last_response_status: number | null
  last_response_headers: Record<string, string> | null
  last_response_body: string | null
  last_response_time_ms: number | null
  history: Array<{
    sent_at: string
    method: string
    url: string
    status: number
    time_ms: number
  }> | null
}

export interface SendResult {
  status: number
  headers: Record<string, string>
  body: string
  time_ms: number
  size: number
}
