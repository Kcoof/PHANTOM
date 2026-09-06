import { useEffect, useRef } from 'react'
import { Send, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { historyService } from '../../services/proxyService'
import { apiError } from '../../services/api'
import { useProxyStore } from '../../stores/proxyStore'
import { useContextMenu, type MenuItem } from '../shared/ContextMenu'
import { formatBytes, formatMs, formatTime, methodClass, statusClass } from '../../utils/formatters'

export function RequestTable() {
  const requests = useProxyStore((s) => s.requests)
  const selectedId = useProxyStore((s) => s.selectedId)
  const selectRequest = useProxyStore((s) => s.selectRequest)
  const refresh = useProxyStore((s) => s.refreshRequests)
  const contextMenu = useContextMenu()
  const lastCountRef = useRef(0)

  useEffect(() => {
    // brief highlight class for rows that arrived via WS
    if (requests.length > lastCountRef.current) {
      const t = setTimeout(() => lastCountRef.current = requests.length, 1300)
      return () => clearTimeout(t)
    }
    lastCountRef.current = requests.length
  }, [requests.length])

  const openMenu = (e: React.MouseEvent, id: number): void => {
    const row = requests.find((r) => r.id === id)
    const items: MenuItem[] = [
      {
        label: 'Send to Repeater',
        onClick: async () => {
          try {
            const { repeater_tab_id } = await historyService.sendToRepeater(id)
            // refresh the repeater store immediately so the tab is there
            // the moment the view is opened (no load-on-mount wait)
            const { useRepeaterStore } = await import('../../stores/repeaterStore')
            void useRepeaterStore.getState().load()
            toast.success(`Sent to Repeater (tab #${repeater_tab_id})`)
          } catch (err) {
            toast.error(apiError(err))
          }
        },
      },
      {
        label: 'Scan this request',
        onClick: async () => {
          try {
            const { scan_id } = await historyService.sendToScanner(id)
            const { useScannerStore } = await import('../../stores/scannerStore')
            void useScannerStore.getState().load()
            toast.success(`Passive scan ${scan_id} started — opening Scanner`)
            window.location.hash = '#/scanner'
          } catch (err) {
            toast.error(apiError(err))
          }
        },
      },
      {
        label: 'AI Analyze',
        onClick: () => {
          const { analyzeRequest } = useProxyStore.getState()
          void analyzeRequest(id, row ? `${row.method} ${row.host}${row.path}` : `request #${id}`)
        },
      },
      {
        label: 'Copy URL',
        onClick: () => {
          if (row) navigator.clipboard?.writeText(row.url)
          toast.success('URL copied')
        },
      },
      {
        label: 'Delete entry',
        danger: true,
        separatorBefore: true,
        onClick: async () => {
          try {
            await historyService.remove(id)
            if (selectedId === id) void selectRequest(null)
            void refresh()
          } catch (err) {
            toast.error(apiError(err))
          }
        },
      },
    ]
    contextMenu.open(e, items)
  }

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <table
        className="mono"
        style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11.5 }}
      >
        <thead style={{ position: 'sticky', top: 0, zIndex: 2 }}>
          <tr style={{ background: 'var(--bg-tertiary)' }}>
            {['#', 'Method', 'Host', 'Path', 'Status', 'Time', 'Size', ''].map((h) => (
              <th
                key={h}
                style={{
                  textAlign: 'left',
                  padding: '6px 8px',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: 10.5,
                  borderBottom: '1px solid var(--border-primary)',
                  whiteSpace: 'nowrap',
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {requests.map((r, i) => {
            const selected = r.id === selectedId
            const isNew = i === 0 && r.id !== undefined && requests.length > 0 && (r as { _new?: boolean })._new
            return (
              <tr
                key={r.id}
                className={isNew ? 'row-new' : ''}
                onClick={() => void selectRequest(selected ? null : r.id)}
                onContextMenu={(e) => openMenu(e, r.id)}
                style={{
                  cursor: 'pointer',
                  background: selected ? 'var(--bg-active)' : i % 2 ? 'var(--bg-secondary)' : 'transparent',
                  borderBottom: '1px solid var(--border-primary)',
                  transition: 'background var(--transition-fast)',
                }}
                onMouseEnter={(e) => {
                  if (!selected) e.currentTarget.style.background = 'var(--bg-hover)'
                }}
                onMouseLeave={(e) => {
                  if (!selected)
                    e.currentTarget.style.background = i % 2 ? 'var(--bg-secondary)' : 'transparent'
                }}
              >
                <td style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>{r.id}</td>
                <td style={{ padding: '4px 8px' }}>
                  <span className={methodClass(r.method)} style={{ fontWeight: 600 }}>
                    {r.method}
                  </span>
                </td>
                <td style={{ padding: '4px 8px', color: 'var(--text-primary)' }}>{r.host}</td>
                <td
                  style={{
                    padding: '4px 8px',
                    color: 'var(--text-secondary)',
                    maxWidth: 300,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {r.path}
                  {r.is_intercepted ? ' ⏸' : ''}
                </td>
                <td style={{ padding: '4px 8px' }}>
                  <span className={statusClass(r.status_code)} style={{ fontWeight: 600 }}>
                    {r.status_code ?? '—'}
                  </span>
                </td>
                <td style={{ padding: '4px 8px', color: 'var(--text-secondary)' }}>{formatMs(r.response_time_ms)}</td>
                <td style={{ padding: '4px 8px', color: 'var(--text-secondary)' }}>{formatBytes(r.size_bytes)}</td>
                <td style={{ padding: '2px 6px' }}>
                  <span title={r.timestamp ? formatTime(r.timestamp) : ''} />
                  <Send size={0} />
                  <Trash2 size={0} />
                </td>
              </tr>
            )
          })}
          {requests.length === 0 && (
            <tr>
              <td
                colSpan={8}
                style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}
              >
                No traffic yet — start the proxy and browse through it.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {contextMenu.element}
    </div>
  )
}
