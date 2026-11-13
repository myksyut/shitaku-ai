import { apiClient } from '../../lib/api-client'
import type { SlackChannel, SlackIntegration, SlackOAuthStartResponse } from './types'

const BASE_PATH = '/api/v1/slack'

export async function startSlackOAuth(): Promise<SlackOAuthStartResponse> {
  const params = new URLSearchParams({ redirect_origin: window.location.origin })
  return apiClient<SlackOAuthStartResponse>(`${BASE_PATH}/auth?${params.toString()}`)
}

export async function getSlackIntegrations(): Promise<SlackIntegration[]> {
  return apiClient<SlackIntegration[]>(`${BASE_PATH}/integrations`)
}

export async function deleteSlackIntegration(integrationId: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/integrations/${integrationId}`, {
    method: 'DELETE',
  })
}

export async function getSlackChannels(integrationId: string): Promise<SlackChannel[]> {
  return apiClient<SlackChannel[]>(`${BASE_PATH}/integrations/${integrationId}/channels`)
}
