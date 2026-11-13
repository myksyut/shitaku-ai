import { apiClient } from '../../lib/api-client'
import type { DictionaryEntry, DictionaryEntryCreate, DictionaryEntryUpdate } from './types'

const basePath = (seriesId: string) => `/api/v1/series/${encodeURIComponent(seriesId)}/dictionary`

export function getDictionaryEntries(seriesId: string, signal?: AbortSignal) {
  return apiClient<DictionaryEntry[]>(basePath(seriesId), { signal })
}

export function createDictionaryEntry(seriesId: string, data: DictionaryEntryCreate) {
  return apiClient<DictionaryEntry>(basePath(seriesId), { method: 'POST', body: JSON.stringify(data) })
}

export function updateDictionaryEntry(seriesId: string, entryId: string, data: DictionaryEntryUpdate) {
  return apiClient<DictionaryEntry>(`${basePath(seriesId)}/${encodeURIComponent(entryId)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteDictionaryEntry(seriesId: string, entryId: string) {
  return apiClient<void>(`${basePath(seriesId)}/${encodeURIComponent(entryId)}`, { method: 'DELETE' })
}
