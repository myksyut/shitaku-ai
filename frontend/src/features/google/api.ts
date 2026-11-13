import { apiClient } from '../../lib/api-client'
import type {
  GoogleIntegration,
  GoogleOAuthStartResponse,
  SyncProviderTokenRequest,
  SyncProviderTokenResponse,
} from './types'

const BASE_PATH = '/api/v1/google'

export function startGoogleOAuth() {
  const params = new URLSearchParams({ redirect_origin: window.location.origin })
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth?${params}`)
}

export function getGoogleIntegrations() {
  return apiClient<GoogleIntegration[]>(`${BASE_PATH}/integrations`)
}

export function deleteGoogleIntegration(integrationId: string) {
  return apiClient<void>(`${BASE_PATH}/integrations/${encodeURIComponent(integrationId)}`, { method: 'DELETE' })
}

export function syncProviderToken(request: SyncProviderTokenRequest) {
  return apiClient<SyncProviderTokenResponse>(`${BASE_PATH}/sync-token`, {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export function startAdditionalScopes(integrationId: string) {
  const params = new URLSearchParams({ integration_id: integrationId, redirect_origin: window.location.origin })
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth/additional-scopes?${params}`)
}
