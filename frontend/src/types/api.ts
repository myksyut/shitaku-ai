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

export type HealthResponse = {
  status: string
}

export type ApiErrorResponse = {
  detail: string
}
