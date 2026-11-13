import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { seriesKeys } from '../series/hooks'
import { createDictionaryEntry, deleteDictionaryEntry, getDictionaryEntries, updateDictionaryEntry } from './api'
import type { DictionaryEntryCreate, DictionaryEntryUpdate } from './types'

export function useDictionaryEntries(seriesId: string) {
  return useQuery({
    queryKey: seriesKeys.dictionary(seriesId),
    queryFn: ({ signal }) => getDictionaryEntries(seriesId, signal),
    enabled: !!seriesId,
  })
}

export function useCreateDictionaryEntry(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (data: DictionaryEntryCreate) => createDictionaryEntry(seriesId, data),
    onSuccess: () => client.invalidateQueries({ queryKey: seriesKeys.dictionary(seriesId), exact: true }),
  })
}

export function useUpdateDictionaryEntry(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, data }: { entryId: string; data: DictionaryEntryUpdate }) =>
      updateDictionaryEntry(seriesId, entryId, data),
    onSuccess: () => client.invalidateQueries({ queryKey: seriesKeys.dictionary(seriesId), exact: true }),
  })
}

export function useDeleteDictionaryEntry(seriesId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) => deleteDictionaryEntry(seriesId, entryId),
    onSuccess: () => client.invalidateQueries({ queryKey: seriesKeys.dictionary(seriesId), exact: true }),
  })
}
