import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './api'
import {
  agentDictionaryKeys,
  dictionaryKeys,
  useAgentDictionaryEntries,
  useCreateAgentDictionaryEntry,
  useDeleteAgentDictionaryEntry,
  useDictionaryEntries,
  useUpdateAgentDictionaryEntry,
} from './hooks'
import type { DictionaryEntry } from './types'

// Mock the API module
vi.mock('./api')

const mockApi = vi.mocked(api)

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

const mockDictionaryEntry: DictionaryEntry = {
  id: 'entry-1',
  agent_id: 'agent-123',
  canonical_name: 'Test Entry',
  category: 'person',
  aliases: ['alias1', 'alias2'],
  description: 'Test description',
  created_at: '2026-01-31T00:00:00Z',
  updated_at: null,
}

describe('Dictionary Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('dictionaryKeys', () => {
    it('should generate correct query keys', () => {
      expect(dictionaryKeys.all).toEqual(['dictionary'])
      expect(dictionaryKeys.lists()).toEqual(['dictionary', 'list'])
      expect(dictionaryKeys.list()).toEqual(['dictionary', 'list'])
      expect(dictionaryKeys.details()).toEqual(['dictionary', 'detail'])
      expect(dictionaryKeys.detail('test-id')).toEqual(['dictionary', 'detail', 'test-id'])
    })
  })

  describe('agentDictionaryKeys', () => {
    it('should generate correct query keys for agent dictionary', () => {
      expect(agentDictionaryKeys.all).toEqual(['agent-dictionary'])
      expect(agentDictionaryKeys.list('agent-123')).toEqual(['agent-dictionary', 'list', 'agent-123'])
    })
  })

  describe('useDictionaryEntries', () => {
    it('should fetch dictionary entries', async () => {
      mockApi.getDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

      const { result } = renderHook(() => useDictionaryEntries(), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual([mockDictionaryEntry])
      expect(mockApi.getDictionaryEntries).toHaveBeenCalledTimes(1)
    })
  })

  describe('useAgentDictionaryEntries', () => {
    it('should fetch agent dictionary entries', async () => {
      const agentId = 'agent-123'
      mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

      const { result } = renderHook(() => useAgentDictionaryEntries(agentId), {
        wrapper: createWrapper(),
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toEqual([mockDictionaryEntry])
      expect(mockApi.getAgentDictionaryEntries).toHaveBeenCalledWith(agentId)
    })

    it('should not fetch when agentId is empty', async () => {
      const { result } = renderHook(() => useAgentDictionaryEntries(''), {
        wrapper: createWrapper(),
      })

      // Query should be disabled
      expect(result.current.fetchStatus).toBe('idle')
      expect(mockApi.getAgentDictionaryEntries).not.toHaveBeenCalled()
    })
  })

  describe('useCreateAgentDictionaryEntry', () => {
    it('should create a new agent dictionary entry', async () => {
      const agentId = 'agent-123'
      const createData = {
        canonical_name: 'New Entry',
        category: 'project' as const,
        aliases: ['alias1'],
      }
      const createdEntry = { ...mockDictionaryEntry, ...createData }
      mockApi.createAgentDictionaryEntry.mockResolvedValue(createdEntry)

      const { result } = renderHook(() => useCreateAgentDictionaryEntry(agentId), {
        wrapper: createWrapper(),
      })

      result.current.mutate(createData)

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockApi.createAgentDictionaryEntry).toHaveBeenCalledWith(agentId, createData)
    })
  })

  describe('useUpdateAgentDictionaryEntry', () => {
    it('should update an agent dictionary entry', async () => {
      const agentId = 'agent-123'
      const entryId = 'entry-1'
      const updateData = {
        canonical_name: 'Updated Entry',
      }
      const updatedEntry = { ...mockDictionaryEntry, ...updateData }
      mockApi.updateAgentDictionaryEntry.mockResolvedValue(updatedEntry)

      const { result } = renderHook(() => useUpdateAgentDictionaryEntry(agentId), {
        wrapper: createWrapper(),
      })

      result.current.mutate({ entryId, data: updateData })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockApi.updateAgentDictionaryEntry).toHaveBeenCalledWith(agentId, entryId, updateData)
    })
  })

  describe('useDeleteAgentDictionaryEntry', () => {
    it('should delete an agent dictionary entry', async () => {
      const agentId = 'agent-123'
      const entryId = 'entry-1'
      mockApi.deleteAgentDictionaryEntry.mockResolvedValue(undefined)

      const { result } = renderHook(() => useDeleteAgentDictionaryEntry(agentId), {
        wrapper: createWrapper(),
      })

      result.current.mutate(entryId)

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(mockApi.deleteAgentDictionaryEntry).toHaveBeenCalledWith(agentId, entryId)
    })
  })
})
