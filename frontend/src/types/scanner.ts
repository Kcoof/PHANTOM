export interface ScanCheckInfo {
  check_type: string
  name: string
  severity: string
  mode: 'passive' | 'active'
  cwe_id: string | null
}

export interface Scan {
  id: string
  timestamp: string
  target_url: string
  scan_type: 'active' | 'passive' | 'full'
  status: 'running' | 'paused' | 'completed' | 'failed'
  total_requests: number
  findings_count: number
  config: string | null
  started_at: string | null
  completed_at: string | null
}

export interface Finding {
  id: number
  scan_id: string
  history_id: number | null
  timestamp: string
  finding_type: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence: 'certain' | 'firm' | 'tentative'
  title: string
  description: string
  url: string
  parameter: string | null
  payload: string | null
  evidence: string | null
  request_dump: string | null
  response_dump: string | null
  remediation: string | null
  cwe_id: string | null
  status: 'open' | 'confirmed' | 'fixed' | 'false_positive'
}

export interface ScanProgressEvent {
  scan_id: string
  status: string
  done: number
  total: number
}
