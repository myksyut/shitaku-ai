import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './api'
import { DictionarySection } from './DictionarySection'
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

const mockDictionaryEntry2: DictionaryEntry = {
  id: 'entry-2',
  agent_id: 'agent-123',
  canonical_name: 'Another Entry',
  category: 'project',
  aliases: [],
  description: null,
  created_at: '2026-01-31T00:00:00Z',
  updated_at: null,
}

describe('DictionarySection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders empty state when no entries', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('辞書エントリがありません')).toBeInTheDocument()
    })
  })

  it('renders loading state initially', async () => {
    mockApi.getAgentDictionaryEntries.mockImplementation(
      () => new Promise(() => {}), // Never resolves to keep loading
    )

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('renders dictionary entries when data is available', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry, mockDictionaryEntry2])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test Entry')).toBeInTheDocument()
    })
    expect(screen.getByText('Another Entry')).toBeInTheDocument()
    expect(screen.getByText('人名')).toBeInTheDocument()
    expect(screen.getByText('プロジェクト')).toBeInTheDocument()
  })

  it('renders error state when API call fails', async () => {
    mockApi.getAgentDictionaryEntries.mockRejectedValue(new Error('Network error'))

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('辞書の読み込みに失敗しました')).toBeInTheDocument()
    })
  })

  it('renders "辞書を追加" button', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '辞書を追加' })).toBeInTheDocument()
    })
  })

  it('opens form modal when "辞書を追加" button is clicked', async () => {
    const user = userEvent.setup()
    mockApi.getAgentDictionaryEntries.mockResolvedValue([])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '辞書を追加' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '辞書を追加' }))

    await waitFor(() => {
      expect(screen.getByText('辞書エントリを追加')).toBeInTheDocument()
    })
  })

  it('renders edit and delete buttons for each entry', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test Entry')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: '編集' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '削除' })).toBeInTheDocument()
  })

  it('opens form modal with entry data when edit button is clicked', async () => {
    const user = userEvent.setup()
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test Entry')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '編集' }))

    await waitFor(() => {
      expect(screen.getByText('辞書エントリを編集')).toBeInTheDocument()
    })
    expect(screen.getByDisplayValue('Test Entry')).toBeInTheDocument()
  })

  it('calls delete API when delete button is clicked and confirmed', async () => {
    const user = userEvent.setup()
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])
    mockApi.deleteAgentDictionaryEntry.mockResolvedValue(undefined)

    // Mock window.confirm
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test Entry')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '削除' }))

    await waitFor(() => {
      expect(mockApi.deleteAgentDictionaryEntry).toHaveBeenCalledWith('agent-123', 'entry-1')
    })
  })

  it('does not call delete API when delete is cancelled', async () => {
    const user = userEvent.setup()
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

    // Mock window.confirm to return false
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test Entry')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '削除' }))

    expect(mockApi.deleteAgentDictionaryEntry).not.toHaveBeenCalled()
  })

  it('displays aliases count when entry has aliases', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('表記揺れ: 2件')).toBeInTheDocument()
    })
  })

  it('displays description when entry has one', async () => {
    mockApi.getAgentDictionaryEntries.mockResolvedValue([mockDictionaryEntry])

    render(<DictionarySection agentId="agent-123" />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Test description')).toBeInTheDocument()
    })
  })
})
