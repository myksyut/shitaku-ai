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

export interface SyncProviderTokenRequest {
  provider_token: string
  provider_refresh_token: string | null
  email: string
  scopes: string[] | null
}

export interface SyncProviderTokenResponse {
  success: boolean
  message: string
  integration_id: string | null
}
