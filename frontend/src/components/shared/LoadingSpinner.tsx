export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        height: '100%',
        minHeight: 60,
        color: 'var(--text-secondary)',
        fontSize: 12,
      }}
    >
      <span
        className="pulse-dot"
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: 'var(--accent-primary)',
          display: 'inline-block',
        }}
      />
      {label ?? 'Loading…'}
    </div>
  )
}
