import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

/** Standardized error detail extraction — every toast uses this (Constitution V). */
export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail) return JSON.stringify(detail)
    const status = error.response?.status
    if (status === 502 || status === 504) {
      return 'backend unreachable on :8899 — is uvicorn running? (scripts/dev.ps1 or scripts/dev.sh)'
    }
    if (status === undefined && error.code === 'ERR_NETWORK') {
      return 'cannot reach the backend — check that uvicorn is running on :8899'
    }
    return error.message
  }
  if (error instanceof Error) return error.message
  return String(error)
}
