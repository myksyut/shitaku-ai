import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (session?.access_token) {
    ;(headers as Record<string, string>).Authorization = `Bearer ${session.access_token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401) {
      await supabase.auth.signOut()
    }
    const error: unknown = await response.json().catch(() => null)
    const message =
      error && typeof error === 'object' && 'detail' in error && typeof error.detail === 'string'
        ? error.detail
        : `HTTP ${response.status}`
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) return undefined as T

  return response.json()
}
