import type { ProxyRequestSummary } from './common'

export interface ProxyStatus {
  running: boolean
  host: string | null
  port: number | null
  requests_captured: number
  intercept_enabled: boolean
  intercept_queue_size: number
}

export interface InterceptedFlow {
  flow_id: string
  method: string
  url: string
  headers: Record<string, string>
  body: string | null
  content_type: string | null
}

export interface NewRequestEvent {
  id: number
  method: string
  host: string
  path: string
  url: string
  status_code: number | null
  response_time_ms: number | null
  size_bytes: number | null
}

export type ProxyRequest = ProxyRequestSummary
