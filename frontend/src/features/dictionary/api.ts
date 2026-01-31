import { apiClient } from '../../lib/api-client'
import type { DictionaryEntry, DictionaryEntryCreate, DictionaryEntryUpdate } from './types'

const BASE_PATH = '/api/v1/dictionary'

export async function getDictionaryEntries(): Promise<DictionaryEntry[]> {
  return apiClient<DictionaryEntry[]>(BASE_PATH)
}

export async function getDictionaryEntry(id: string): Promise<DictionaryEntry> {
  return apiClient<DictionaryEntry>(`${BASE_PATH}/${id}`)
}

export async function createDictionaryEntry(data: DictionaryEntryCreate): Promise<DictionaryEntry> {
  return apiClient<DictionaryEntry>(BASE_PATH, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDictionaryEntry(id: string, data: DictionaryEntryUpdate): Promise<DictionaryEntry> {
  return apiClient<DictionaryEntry>(`${BASE_PATH}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDictionaryEntry(id: string): Promise<void> {
  await apiClient<void>(`${BASE_PATH}/${id}`, {
    method: 'DELETE',
  })
}
