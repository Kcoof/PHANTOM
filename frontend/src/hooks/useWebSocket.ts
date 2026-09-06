import { useEffect, useRef } from 'react'
import { useProxyStore } from '../stores/proxyStore'
import { useScannerStore } from '../stores/scannerStore'

type Handler = (data: unknown) => void

/**
 * Live event stream hook (Constitution III — no polling).
 * Auto-reconnects with backoff; handlers re-sync state on reconnect.
 */
export function usePhantomWebSocket(onEvent?: Handler): void {
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const timerRef = useRef<number | null>(null)
  const handlerRef = useRef<Handler | undefined>(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    let closed = false

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws`)
      wsRef.current = ws

      ws.onopen = () => {
        retryRef.current = 0
        useProxyStore.getState().setWsConnected(true)
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string)
          if (msg.event === 'pong') return
          useProxyStore.getState().handleWsEvent(msg.event, msg.data)
          useScannerStore.getState().handleWsEvent(msg.event, msg.data)
          handlerRef.current?.(msg)
        } catch {
          /* ignore malformed frame */
        }
      }

      ws.onclose = () => {
        useProxyStore.getState().setWsConnected(false)
        if (closed) return
        const delay = Math.min(1000 * 2 ** retryRef.current, 10_000)
        retryRef.current += 1
        timerRef.current = window.setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    const pingTimer = window.setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ event: 'ping' }))
      }
    }, 15_000)

    return () => {
      closed = true
      if (timerRef.current) window.clearTimeout(timerRef.current)
      window.clearInterval(pingTimer)
      wsRef.current?.close()
    }
  }, [])
}
