import Editor from '@monaco-editor/react'

interface RequestEditorProps {
  value: string
  onChange: (value: string) => void
}

/** Monaco raw HTTP editor (Constitution IV: no plain textareas). */
export function RequestEditor({ value, onChange }: RequestEditorProps) {
  return (
    <Editor
      height="100%"
      defaultLanguage="ini"
      value={value}
      onChange={(v) => onChange(v ?? '')}
      theme="vs-dark"
      options={{
        fontFamily: 'JetBrains Mono, Consolas, monospace',
        fontSize: 12,
        minimap: { enabled: false },
        lineNumbers: 'off',
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        padding: { top: 10 },
        renderLineHighlight: 'none',
        automaticLayout: true,
      }}
      loading={
        <div className="skeleton" style={{ width: '100%', height: '100%' }} />
      }
    />
  )
}
