import { useEffect, useRef } from 'react'
import { useProxyStore } from '../stores/proxyStore'
import { useScannerStore } from '../stores/scannerStore'
import { useIntruderStore } from '../stores/intruderStore'

type Handler = (data: unknown) => void

const CONNECT_TIMEOUT_MS = 4000

/**
 * Live event stream hook (Constitution III — no polling).
 * Auto-reconnects with backoff, resyncs state after recovery, and never lets a
 * half-open CONNECTING socket stall the retry loop (connect watchdog).
 */
export function usePhantomWebSocket(onEvent?: Handler): void {
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const timerRef = useRef<number | null>(null)
  const watchdogRef = useRef<number | null>(null)
  const epochRef = useRef(0)
  const handlerRef = useRef<Handler | undefined>(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    epochRef.current += 1
    const myEpoch = epochRef.current

    const clearTimers = () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
      if (watchdogRef.current) window.clearTimeout(watchdogRef.current)
      timerRef.current = null
      watchdogRef.current = null
    }

    const scheduleReconnect = () => {
      // Only the newest generation schedules reconnects; stale sockets'
      // close events must not spawn parallel retry loops.
      if (myEpoch !== epochRef.current) return
      clearTimers()
      const delay = Math.min(1000 * 2 ** retryRef.current, 10_000)
      retryRef.current += 1
      timerRef.current = window.setTimeout(connect, delay)
    }

    const connect = () => {
      if (myEpoch !== epochRef.current) return
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      let ws: WebSocket
      try {
        ws = new WebSocket(`${proto}://${location.host}/ws`)
      } catch {
        scheduleReconnect()
        return
      }
      wsRef.current = ws

      // Connect watchdog: if the socket is still CONNECTING after a few
      // seconds (proxy accepted TCP but backend never completes the
      // handshake), force-close so the retry loop continues.
      watchdogRef.current = window.setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) ws.close()
      }, CONNECT_TIMEOUT_MS)

      ws.onopen = () => {
        if (myEpoch !== epochRef.current) {
          ws.close()
          return
        }
        if (watchdogRef.current) window.clearTimeout(watchdogRef.current)
        retryRef.current = 0
        useProxyStore.getState().setWsConnected(true)
        // Resync after any outage: server state moved on without us.
        void useProxyStore.getState().refreshRequests()
        void useProxyStore.getState().refreshStatus()
        void useScannerStore.getState().load()
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string)
          if (msg.event === 'pong') return
          useProxyStore.getState().handleWsEvent(msg.event, msg.data)
          useScannerStore.getState().handleWsEvent(msg.event, msg.data)
          useIntruderStore.getState().handleWsEvent(msg.event, msg.data)
          handlerRef.current?.(msg)
        } catch {
          /* ignore malformed frame */
        }
      }

      ws.onclose = () => {
        if (myEpoch !== epochRef.current) return
        useProxyStore.getState().setWsConnected(false)
        scheduleReconnect()
      }

      ws.onerror = () => {
        // onclose follows onerror; nothing else to do here.
      }
    }

    connect()
    const pingTimer = window.setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ event: 'ping' }))
      }
    }, 15_000)

    return () => {
      epochRef.current += 1 // invalidate this generation's handlers
      clearTimers()
      window.clearInterval(pingTimer)
      const ws = wsRef.current
      wsRef.current = null
      if (ws && ws.readyState <= WebSocket.OPEN) {
        ws.onclose = null
        ws.onmessage = null
        ws.onerror = null
        ws.close()
      }
    }
  }, [])
}
