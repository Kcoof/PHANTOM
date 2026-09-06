export function ModulePlaceholder({ title, note }: { title: string; note: string }) {
  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        color: 'var(--text-muted)',
      }}
      className="fade-in"
    >
      <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: 1 }}>
        {title}
      </div>
      <div style={{ fontSize: 12, maxWidth: 380, textAlign: 'center', lineHeight: 1.6 }}>{note}</div>
    </div>
  )
}
