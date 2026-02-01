export interface GoogleIntegration {
  id: string
  email: string
  granted_scopes: string[]
  created_at: string
  updated_at: string | null
}

export interface GoogleOAuthStartResponse {
  authorize_url: string
}
