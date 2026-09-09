/** Shared response-to-browser rendering (Repeater globe + Proxy context menu). */

const BLOCK_MARKERS = [
  'automated process',
  'request has been blocked',
  'access denied',
  'attention required',
  'captcha',
  'unusual traffic',
]

function injectBase(html: string, baseUrl: string): string {
  const baseTag = `<base href="${baseUrl}">`
  if (/<head[^>]*>/i.test(html)) return html.replace(/<head([^>]*)>/i, `<head$1>${baseTag}`)
  if (/<html[^>]*>/i.test(html)) return html.replace(/<html([^>]*)>/i, `<html$1><head>${baseTag}</head>`)
  return `${baseTag}<html><body>${html}</body></html>`
}

export function looksBotBlocked(body: string): boolean {
  const head = body.slice(0, 4000).toLowerCase()
  return BLOCK_MARKERS.some((m) => head.includes(m))
}

/** Open a captured/sent response rendered as a page in a new browser tab. */
export function renderResponseInBrowser(body: string, baseUrl: string, contentType?: string | null) {
  if (!body) return
  const ct = (contentType ?? '').toLowerCase()
  const isHtml = ct.includes('html') || /^\s*<(?:!doctype|html)/i.test(body)
  let payload: string
  let blob: Blob
  if (isHtml) {
    payload = injectBase(body, baseUrl)
    if (looksBotBlocked(body)) {
      const notice =
        '<div style="position:sticky;top:0;z-index:2147483647;background:#2d1e05;color:#ffc107;' +
        'font:600 12px/1.6 sans-serif;padding:8px 14px;border-bottom:1px solid #ffc10755">' +
        '⚠ PHANTOM: this response looks like a bot-block / challenge page — the site may be ' +
        'fingerprinting the client. Re-send from a request captured by your real browser, or ' +
        'render the original captured response from Proxy history.</div>'
      payload = payload.replace(/<body([^>]*)>/i, `<body$1>${notice}`) || notice + payload
    }
    blob = new Blob([payload], { type: 'text/html' })
  } else {
    blob = new Blob([body], { type: 'text/plain' })
  }
  const url = URL.createObjectURL(blob)
  const win = window.open(url, '_blank')
  if (!win) {
    const a = document.createElement('a')
    a.href = url
    a.target = '_blank'
    a.rel = 'noopener'
    a.click()
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
}
