/**
 * MeetingNote API functions
 */

import { apiClient } from '../../lib/api-client'
import type { MeetingNote, MeetingNoteCreate, MeetingNoteUploadResponse } from './types'

const BASE_PATH = '/api/v1/meeting-notes'

export async function getMeetingNotes(agentId: string, limit?: number): Promise<MeetingNote[]> {
  const params = new URLSearchParams({ agent_id: agentId })
  if (limit) {
    params.append('limit', String(limit))
  }
  return apiClient<MeetingNote[]>(`${BASE_PATH}?${params.toString()}`)
}

export async function getMeetingNote(id: string): Promise<MeetingNote> {
  return apiClient<MeetingNote>(`${BASE_PATH}/${id}`)
}

export async function uploadMeetingNote(data: MeetingNoteCreate): Promise<MeetingNoteUploadResponse> {
  return apiClient<MeetingNoteUploadResponse>(BASE_PATH, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteMeetingNote(id: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/${id}`, {
    method: 'DELETE',
  })
}
