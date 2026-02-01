import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AgentDictionaryForm } from './AgentDictionaryForm'
import * as api from './api'
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

describe('AgentDictionaryForm', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Add mode (entry is null)', () => {
    it('renders form with empty fields in add mode', () => {
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByText('辞書エントリを追加')).toBeInTheDocument()
      expect(screen.getByLabelText(/正式名称/)).toHaveValue('')
      expect(screen.getByLabelText(/カテゴリ/)).toBeInTheDocument()
    })

    it('shows validation error when canonical_name is empty', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.click(screen.getByRole('button', { name: '作成' }))

      await waitFor(() => {
        expect(screen.getByText('正式名称は必須です')).toBeInTheDocument()
      })
    })

    it('calls createAgentDictionaryEntry when form is submitted', async () => {
      const user = userEvent.setup()
      mockApi.createAgentDictionaryEntry.mockResolvedValue({
        ...mockDictionaryEntry,
        canonical_name: 'New Entry',
      })

      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.type(screen.getByLabelText(/正式名称/), 'New Entry')
      await user.click(screen.getByRole('button', { name: '作成' }))

      await waitFor(() => {
        expect(mockApi.createAgentDictionaryEntry).toHaveBeenCalledWith('agent-123', {
          canonical_name: 'New Entry',
          category: 'term',
          aliases: [],
          description: null,
        })
      })
      expect(mockOnClose).toHaveBeenCalled()
    })

    it('displays error message when API call fails', async () => {
      const user = userEvent.setup()
      mockApi.createAgentDictionaryEntry.mockRejectedValue(new Error('API Error'))

      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.type(screen.getByLabelText(/正式名称/), 'New Entry')
      await user.click(screen.getByRole('button', { name: '作成' }))

      await waitFor(() => {
        expect(screen.getByText('保存に失敗しました')).toBeInTheDocument()
      })
      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Edit mode (entry is provided)', () => {
    it('renders form with existing entry data', () => {
      render(<AgentDictionaryForm agentId="agent-123" entry={mockDictionaryEntry} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByText('辞書エントリを編集')).toBeInTheDocument()
      expect(screen.getByLabelText(/正式名称/)).toHaveValue('Test Entry')
      expect(screen.getByLabelText(/カテゴリ/)).toHaveValue('person')
      expect(screen.getByText('alias1')).toBeInTheDocument()
      expect(screen.getByText('alias2')).toBeInTheDocument()
    })

    it('calls updateAgentDictionaryEntry when form is submitted', async () => {
      const user = userEvent.setup()
      mockApi.updateAgentDictionaryEntry.mockResolvedValue({
        ...mockDictionaryEntry,
        canonical_name: 'Updated Entry',
      })

      render(<AgentDictionaryForm agentId="agent-123" entry={mockDictionaryEntry} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.clear(screen.getByLabelText(/正式名称/))
      await user.type(screen.getByLabelText(/正式名称/), 'Updated Entry')
      await user.click(screen.getByRole('button', { name: '更新' }))

      await waitFor(() => {
        expect(mockApi.updateAgentDictionaryEntry).toHaveBeenCalledWith('agent-123', 'entry-1', {
          canonical_name: 'Updated Entry',
          category: 'person',
          aliases: ['alias1', 'alias2'],
          description: 'Test description',
        })
      })
      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Alias input', () => {
    it('adds alias when Enter key is pressed', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      const aliasInput = screen.getByPlaceholderText('Enter または カンマ で追加')
      await user.type(aliasInput, 'newAlias{Enter}')

      expect(screen.getByText('newAlias')).toBeInTheDocument()
    })

    it('adds alias when comma is pressed', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      const aliasInput = screen.getByPlaceholderText('Enter または カンマ で追加')
      await user.type(aliasInput, 'newAlias,')

      expect(screen.getByText('newAlias')).toBeInTheDocument()
    })

    it('removes alias when x button is clicked', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={mockDictionaryEntry} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      expect(screen.getByText('alias1')).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: 'alias1を削除' }))

      expect(screen.queryByText('alias1')).not.toBeInTheDocument()
    })

    it('does not add duplicate aliases', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={mockDictionaryEntry} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      const aliasInput = screen.getByPlaceholderText('Enter または カンマ で追加')
      await user.type(aliasInput, 'alias1{Enter}')

      // Should still only have one alias1
      const aliases = screen.getAllByText('alias1')
      expect(aliases).toHaveLength(1)
    })
  })

  describe('Modal behavior', () => {
    it('calls onClose when cancel button is clicked', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.click(screen.getByRole('button', { name: 'キャンセル' }))

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('disables submit button while submitting', async () => {
      const user = userEvent.setup()
      // Create a promise that never resolves
      mockApi.createAgentDictionaryEntry.mockImplementation(() => new Promise(() => {}))

      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.type(screen.getByLabelText(/正式名称/), 'New Entry')
      await user.click(screen.getByRole('button', { name: '作成' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /処理中/ })).toBeDisabled()
      })
    })
  })

  describe('Category selection', () => {
    it('allows changing category', async () => {
      const user = userEvent.setup()
      render(<AgentDictionaryForm agentId="agent-123" entry={null} onClose={mockOnClose} />, {
        wrapper: createWrapper(),
      })

      await user.selectOptions(screen.getByLabelText(/カテゴリ/), 'project')

      expect(screen.getByLabelText(/カテゴリ/)).toHaveValue('project')
    })
  })
})
