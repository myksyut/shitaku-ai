const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: unknown
  headers?: Record<string, string>
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new ApiError(errorData?.detail || 'API request failed', response.status, errorData)
  }

  return response.json()
}

// API endpoints
export const api = {
  health: {
    check: () => apiClient<{ status: string }>('/health'),
  },
  users: {
    list: (skip = 0, limit = 100) =>
      apiClient<User[]>(`/users/?skip=${skip}&limit=${limit}`),
    get: (id: number) => apiClient<User>(`/users/${id}`),
    create: (data: CreateUserRequest) =>
      apiClient<User>('/users/', { method: 'POST', body: data }),
    update: (id: number, data: UpdateUserRequest) =>
      apiClient<User>(`/users/${id}`, { method: 'PATCH', body: data }),
    delete: (id: number) =>
      apiClient<void>(`/users/${id}`, { method: 'DELETE' }),
  },
}

// Types
export type User = {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export type CreateUserRequest = {
  email: string
  password: string
  full_name?: string
}

export type UpdateUserRequest = {
  email?: string
  password?: string
  full_name?: string
}
