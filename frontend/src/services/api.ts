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
    return error.message
  }
  if (error instanceof Error) return error.message
  return String(error)
}
