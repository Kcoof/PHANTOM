import { useEffect, useState } from 'react'
import { ArrowRight, Copy, Plus, Search, Trash2, Wand2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { decoderService, type AutoDetectResult } from '../../services/decoderService'
import { apiError } from '../../services/api'
import { copyToClipboard } from '../../utils/formatters'

type Op = { kind: 'encode' | 'decode'; codec: string } | { kind: 'hash'; codec: string }

const CODECS = ['base64', 'url', 'html', 'hex', 'unicode', 'gzip', 'jwt']
const HASHES = ['md5', 'sha1', 'sha256', 'sha512']

interface ChainStep {
  id: number
  op: Op
  output: string
  error: string | null
}

let nextId = 1

export function DecoderView() {
  const [input, setInput] = useState('')
  const [chain, setChain] = useState<ChainStep[]>([])
  const [detect, setDetect] = useState<AutoDetectResult[] | null>(null)

  const currentInput = chain.length ? chain[chain.length - 1].output : input

  const runOp = async (op: Op) => {
    const step: ChainStep = { id: nextId++, op, output: '', error: null }
    setChain((c) => [...c, step])
    try {
      let output: string
      if (op.kind === 'hash') {
        output = await decoderService.hash(currentInput, op.codec)
      } else if (op.kind === 'encode') {
        output = await decoderService.encode(currentInput, op.codec)
      } else {
        output = await decoderService.decode(currentInput, op.codec)
      }
      setChain((c) => c.map((s) => (s.id === step.id ? { ...s, output } : s)))
    } catch (err) {
      const msg = apiError(err)
      setChain((c) => c.map((s) => (s.id === step.id ? { ...s, error: msg } : s)))
      toast.error(msg)
    }
  }

  const autoDetect = async () => {
    try {
      const results = await decoderService.autoDetect(input)
      setDetect(results)
      if (results.length === 0) toast('No known encodings detected', { icon: '🤔' })
    } catch (err) {
      toast.error(apiError(err))
    }
  }

  useEffect(() => {
    setDetect(null)
  }, [input])

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 14, gap: 10, overflow: 'auto' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: 0.5 }}>Decoder</span>
        <div style={{ flex: 1 }} />
        <button className="btn sm" onClick={() => void autoDetect()} disabled={!input.trim()}>
          <Wand2 size={12} /> Auto-detect
        </button>
        <button className="btn sm danger" onClick={() => { setChain([]); setInput(''); setDetect(null) }}>
          <Trash2 size={12} /> Reset
        </button>
      </div>

      {/* input */}
      <textarea
        className="input mono"
        placeholder="Paste data to encode / decode / hash…"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        rows={3}
        style={{ resize: 'vertical', fontSize: 12 }}
      />

      {/* op picker */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {(['decode', 'encode'] as const).map((kind) =>
          CODECS.map((codec) => (
            <button
              key={`${kind}-${codec}`}
              className="btn sm ghost"
              onClick={() => void runOp({ kind, codec })}
              disabled={!currentInput.trim()}
            >
              {kind === 'decode' ? '⇩' : '⇧'} {codec}
            </button>
          )),
        )}
        {HASHES.map((h) => (
          <button key={h} className="btn sm ghost" style={{ color: 'var(--accent-secondary)' }} onClick={() => void runOp({ kind: 'hash', codec: h })} disabled={!currentInput.trim()}>
            # {h}
          </button>
        ))}
      </div>

      {/* auto-detect results */}
      {detect && detect.length > 0 && (
        <div className="panel fade-in" style={{ padding: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1, color: 'var(--text-secondary)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Search size={11} /> AUTO-DETECT
          </div>
          {detect.map((r) => (
            <div key={r.codec} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span className="badge" style={{ background: 'var(--bg-hover)' }}>{r.codec}</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{Math.round(r.confidence * 100)}%</span>
              <span className="mono" style={{ flex: 1, fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.output.slice(0, 120)}</span>
              <button className="btn ghost sm" onClick={() => { setInput(r.output); setChain([]); setDetect(null) }}>
                <Plus size={11} /> use
              </button>
            </div>
          ))}
        </div>
      )}

      {/* chain */}
      {chain.map((step, i) => (
        <div key={step.id} className="panel fade-in" style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="badge" style={{ background: 'var(--accent-glow)', color: 'var(--text-primary)' }}>
              {step.op.kind} · {step.op.codec}
            </span>
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>step {i + 1}</span>
            <div style={{ flex: 1 }} />
            <button className="btn ghost sm" onClick={() => { copyToClipboard(step.output); toast.success('Copied') }}>
              <Copy size={11} />
            </button>
            <button className="btn ghost sm" onClick={() => setChain((c) => c.filter((s) => s.id !== step.id))}>
              <Trash2 size={11} />
            </button>
          </div>
          {step.error ? (
            <div className="mono" style={{ color: 'var(--severity-critical)', fontSize: 11.5 }}>{step.error}</div>
          ) : (
            <pre className="mono" style={{ fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 160, overflow: 'auto' }}>
              {step.output}
            </pre>
          )}
        </div>
      ))}

      {chain.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: 11 }}>
          <ArrowRight size={12} /> final value feeds the next operation
        </div>
      )}
    </div>
  )
}
