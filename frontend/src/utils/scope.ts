import type { ScopeRule } from '../services/settingsService'

/** Glob host pattern (e.g. `*.example.com`) → anchored case-insensitive regex. */
export function hostPatternToRegex(pattern: string): RegExp {
  const escaped = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*/g, '.*')
    .replace(/\?/g, '.')
  return new RegExp(`^${escaped}$`, 'i')
}

/**
 * Subdomain-aware host matching (Burp-style 'include all subdomains'):
 * `example.com` matches the apex AND all subdomains; `*.example.com`
 * matches subdomains AND the apex; suffix-safe (notexample.com ✗).
 */
export function hostMatchesPattern(host: string, pattern: string): boolean {
  const h = host.toLowerCase().trim()
  const p = pattern.toLowerCase().trim()
  if (h === p) return true
  try {
    if (hostPatternToRegex(p).test(h)) return true
  } catch {
    /* fall through to suffix matching */
  }
  const base = p.startsWith('*.') ? p.slice(2) : p
  return h === base || h.endsWith('.' + base)
}

/**
 * Burp-style scope evaluation against live rules: host matches at least one
 * active include rule (or there are no include rules = everything in scope)
 * and no exclude rule.
 */
export function hostInScope(rules: ScopeRule[], host: string): boolean {
  const active = rules.filter((r) => r.is_active === 1 || r.is_active === true)
  const excludes = active.filter((r) => r.rule_type === 'exclude')
  const includes = active.filter((r) => r.rule_type === 'include')
  if (excludes.some((r) => hostMatchesPattern(host, r.host_pattern))) return false
  if (includes.length === 0) return true
  return includes.some((r) => hostMatchesPattern(host, r.host_pattern))
}
