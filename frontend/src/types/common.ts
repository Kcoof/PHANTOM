export interface ProxyRequestSummary {
  id: number
  timestamp?: string
  method: string
  scheme: string
  host: string
  port: number
  path: string
  query_string?: string | null
  url: string
  request_content_type?: string | null
  status_code: number | null
  response_content_type?: string | null
  response_time_ms: number | null
  size_bytes: number | null
  is_intercepted: number | boolean
  is_in_scope: number | boolean
  tags: string[]
  notes?: string | null
  highlight_color?: string | null
}

export interface ProxyRequestDetail extends ProxyRequestSummary {
  request_headers: Record<string, string>
  request_body: string | null
  response_headers: Record<string, string> | null
  response_body: string | null
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface WsMessage {
  event: string
  data: unknown
}
