export type User = {
  id: number
  email: string
  display_name: string
  is_active: boolean
  role: { id: number; name: string; description: string; permissions: string[] }
  created_at: string
}

export type AuditEvent = {
  id: number
  actor_email: string
  action: string
  object_type: string
  object_id: string
  created_at: string
}

export type Page<T> = { items: T[]; total: number; limit: number; offset: number }

let csrfToken = ''

export async function refreshCsrf(): Promise<void> {
  const response = await fetch('/api/v1/auth/csrf', { credentials: 'include' })
  const data = await response.json()
  csrfToken = data.csrf_token
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (!['GET', 'HEAD', 'OPTIONS'].includes((init.method ?? 'GET').toUpperCase())) headers.set('X-CSRF-Token', csrfToken)
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}