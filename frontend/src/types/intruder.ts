export interface IntruderAttack {
  id: string
  name: string
  status: 'running' | 'completed' | 'stopped' | 'failed'
  total: number
  done: number
  created_at: string
  baseline_status: number | null
  baseline_length: number | null
  raw_template?: string
  payloads?: string[]
  grep_patterns?: string[]
}

export interface IntruderResult {
  id: number
  attack_id: string
  idx: number
  payload: string | null
  status: number
  length: number
  time_ms: number
  matched: string[]
  is_baseline: boolean
  url: string
  deviates?: boolean
  response_body?: string
}

export interface SearchResult {
  id: number
  method: string
  url: string
  status_code: number | null
  where: string
  snippet: string
}

export interface MatchReplaceRule {
  id: number
  enabled: boolean | number
  location: 'request' | 'response'
  match_type: 'literal' | 'regex'
  match_value: string
  replace_value: string
  comment: string | null
}
