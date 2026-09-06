interface BadgeProps {
  color?: string
  bg?: string
  children: React.ReactNode
}

export function Badge({ color, bg, children }: BadgeProps) {
  return (
    <span
      className="badge"
      style={{
        color: color ?? 'var(--text-primary)',
        background: bg ?? 'var(--bg-tertiary)',
        border: `1px solid ${color ? `${color}55` : 'var(--border-primary)'}`,
      }}
    >
      {children}
    </span>
  )
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'var(--severity-critical)',
  high: 'var(--severity-high)',
  medium: 'var(--severity-medium)',
  low: 'var(--severity-low)',
  info: 'var(--severity-info)',
}

export function SeverityBadge({ severity }: { severity: string }) {
  const color = SEVERITY_COLORS[severity] ?? 'var(--text-secondary)'
  return (
    <Badge color={color} bg={`${color}18`}>
      {severity.toUpperCase()}
    </Badge>
  )
}
