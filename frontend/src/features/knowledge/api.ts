/**
 * Knowledge API functions
 */

import { apiClient } from '../../lib/api-client'
import type { Knowledge, KnowledgeCreate, KnowledgeUploadResponse } from './types'

const BASE_PATH = '/api/v1/knowledge'

export async function getKnowledgeList(agentId: string, limit?: number): Promise<Knowledge[]> {
  const params = new URLSearchParams({ agent_id: agentId })
  if (limit) {
    params.append('limit', String(limit))
  }
  return apiClient<Knowledge[]>(`${BASE_PATH}?${params.toString()}`)
}

export async function getKnowledge(id: string): Promise<Knowledge> {
  return apiClient<Knowledge>(`${BASE_PATH}/${id}`)
}

export async function uploadKnowledge(data: KnowledgeCreate): Promise<KnowledgeUploadResponse> {
  return apiClient<KnowledgeUploadResponse>(BASE_PATH, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteKnowledge(id: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/${id}`, {
    method: 'DELETE',
  })
}
