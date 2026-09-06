import { useCallback, useRef, useState, type ReactNode } from 'react'

interface SplitPaneProps {
  left: ReactNode
  right: ReactNode
  initial?: number // percent for left pane
  min?: number
  max?: number
  className?: string
}

/** Draggable split pane (Constitution IV: resizable request/response panes). */
export function SplitPane({ left, right, initial = 50, min = 15, max = 85, className }: SplitPaneProps) {
  const [split, setSplit] = useState(initial)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const dragging = useRef(false)

  const onMove = useCallback(
    (clientX: number) => {
      const el = containerRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const pct = ((clientX - rect.left) / rect.width) * 100
      setSplit(Math.min(max, Math.max(min, pct)))
    },
    [min, max],
  )

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ display: 'flex', height: '100%', overflow: 'hidden' }}
      onMouseUp={() => (dragging.current = false)}
      onMouseLeave={() => (dragging.current = false)}
      onMouseMove={(e) => dragging.current && onMove(e.clientX)}
    >
      <div style={{ width: `${split}%`, minWidth: 0, overflow: 'auto' }}>{left}</div>
      <div
        role="separator"
        style={{
          width: 5,
          flex: '0 0 auto',
          cursor: 'col-resize',
          background: 'var(--border-primary)',
          transition: 'background var(--transition-fast)',
        }}
        onMouseDown={() => (dragging.current = true)}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-primary)')}
        onMouseLeave={(e) => {
          if (!dragging.current) e.currentTarget.style.background = 'var(--border-primary)'
        }}
      />
      <div style={{ flex: 1, minWidth: 0, overflow: 'auto' }}>{right}</div>
    </div>
  )
}
