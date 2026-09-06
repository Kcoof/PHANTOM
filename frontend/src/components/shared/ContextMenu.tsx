import { useEffect, useRef, useState, type ReactNode } from 'react'

export interface MenuItem {
  label: string
  onClick: () => void
  danger?: boolean
  separatorBefore?: boolean
}

interface ContextMenuState {
  x: number
  y: number
  items: MenuItem[]
}

/** Right-click context menu used by the proxy history table. */
export function useContextMenu() {
  const [menu, setMenu] = useState<ContextMenuState | null>(null)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!menu) return
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setMenu(null)
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [menu])

  const open = (e: React.MouseEvent, items: MenuItem[]) => {
    e.preventDefault()
    e.stopPropagation()
    setMenu({ x: e.clientX, y: e.clientY, items })
  }

  const element: ReactNode = menu ? (
    <div
      ref={ref}
      className="fade-in"
      style={{
        position: 'fixed',
        left: Math.min(menu.x, window.innerWidth - 200),
        top: Math.min(menu.y, window.innerHeight - menu.items.length * 30 - 20),
        zIndex: 1000,
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-active)',
        borderRadius: 'var(--radius-md)',
        padding: 4,
        minWidth: 180,
        boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
      }}
    >
      {menu.items.map((item, i) => (
        <div key={i}>
          {item.separatorBefore && (
            <div style={{ height: 1, background: 'var(--border-primary)', margin: '4px 0' }} />
          )}
          <button
            className="btn ghost"
            style={{
              width: '100%',
              justifyContent: 'flex-start',
              border: 'none',
              color: item.danger ? 'var(--severity-critical)' : 'var(--text-primary)',
            }}
            onClick={() => {
              item.onClick()
              setMenu(null)
            }}
          >
            {item.label}
          </button>
        </div>
      ))}
    </div>
  ) : null

  return { open, element }
}
