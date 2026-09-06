export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

export function statusClass(status: number | null | undefined): string {
  if (status == null) return 'status-none'
  if (status < 300) return 'status-2xx'
  if (status < 400) return 'status-3xx'
  if (status < 500) return 'status-4xx'
  return 'status-5xx'
}

export function methodClass(method: string): string {
  return `method-${method.toUpperCase()}`
}

export function formatTime(ts: string | null | undefined): string {
  if (!ts) return '—'
  return ts.slice(11, 19)
}

export function copyToClipboard(text: string): void {
  navigator.clipboard?.writeText(text).catch(() => undefined)
}
