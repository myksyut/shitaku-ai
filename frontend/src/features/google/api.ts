import { apiClient } from '../../lib/api-client'
import type { GoogleIntegration, GoogleOAuthStartResponse } from './types'

const BASE_PATH = '/api/v1/google'

export async function startGoogleOAuth(): Promise<GoogleOAuthStartResponse> {
  return apiClient<GoogleOAuthStartResponse>(`${BASE_PATH}/auth`)
}

export async function getGoogleIntegrations(): Promise<GoogleIntegration[]> {
  return apiClient<GoogleIntegration[]>(`${BASE_PATH}/integrations`)
}

export async function deleteGoogleIntegration(integrationId: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/integrations/${integrationId}`, {
    method: 'DELETE',
  })
}
