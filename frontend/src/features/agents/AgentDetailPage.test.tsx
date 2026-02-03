/**
 * AgentDetailPage Reference Settings Tests
 * Design Doc: docs/design/agent-reference-settings-design.md
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Agent } from './types'

// Mock API modules
const mockGetAgent = vi.fn()
const mockUpdateAgent = vi.fn()

vi.mock('./api', () => ({
  getAgent: () => mockGetAgent(),
  updateAgent: (id: string, data: unknown) => mockUpdateAgent(id, data),
  getAgents: vi.fn().mockResolvedValue([]),
  createAgent: vi.fn(),
  deleteAgent: vi.fn(),
}))

// Mock other hooks used by AgentDetailPage
vi.mock('../knowledge/hooks', () => ({
  useKnowledgeList: () => ({ data: [], isLoading: false }),
  useUploadKnowledge: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteKnowledge: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('../slack/hooks', () => ({
  useSlackIntegrations: () => ({ data: [], isLoading: false }),
  useSlackChannels: () => ({ data: [], isLoading: false }),
}))

vi.mock('../google/hooks', () => ({
  useAgentRecurringMeetings: () => ({ data: [], isLoading: false }),
  useUnlinkRecurringMeeting: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

vi.mock('../dictionary/DictionarySection', () => ({
  DictionarySection: () => <div data-testid="dictionary-section">Dictionary Section</div>,
}))

vi.mock('./RecurringMeetingSelector', () => ({
  RecurringMeetingSelector: () => <div data-testid="recurring-meeting-selector">Recurring Meeting Selector</div>,
}))

// Import after mocks
import { AgentDetailPage } from './AgentDetailPage'

const mockAgent: Agent = {
  id: 'agent-1',
  name: 'Test Agent',
  description: 'Test Description',
  slack_channel_id: null,
  created_at: '2026-02-01T00:00:00Z',
  updated_at: null,
  transcript_count: 3,
  slack_message_days: 7,
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/agents/agent-1']}>
          <Routes>
            <Route path="/agents/:agentId" element={children} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('AgentDetailPage - Reference Settings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetAgent.mockResolvedValue(mockAgent)
    mockUpdateAgent.mockResolvedValue({ ...mockAgent })
  })

  const openSettingsModal = async (user: ReturnType<typeof userEvent.setup>) => {
    // Wait for agent to load
    await waitFor(() => {
      expect(screen.getByText('Test Agent')).toBeInTheDocument()
    })

    // Click settings button to open modal
    const settingsButton = screen.getByRole('button', { name: /詳細設定/i })
    await user.click(settingsButton)

    // Wait for modal to appear
    await waitFor(() => {
      expect(screen.getByText('アジェンダ生成参照設定')).toBeInTheDocument()
    })
  }

  it('should display current reference settings', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    // Check that inputs display correct values
    const transcriptInput = screen.getByLabelText(/トランスクリプト参照件数/i)
    expect(transcriptInput).toHaveValue(3)

    const slackDaysInput = screen.getByLabelText(/Slackメッセージ取得日数/i)
    expect(slackDaysInput).toHaveValue(7)
  })

  it('should update transcript_count when changed and saved', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    const transcriptInput = screen.getByLabelText(/トランスクリプト参照件数/i)
    await user.clear(transcriptInput)
    await user.type(transcriptInput, '5')

    const saveButton = screen.getByRole('button', { name: /参照設定を保存/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockUpdateAgent).toHaveBeenCalledWith('agent-1', expect.objectContaining({ transcript_count: 5 }))
    })
  })

  it('should update slack_message_days when changed and saved', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    const slackDaysInput = screen.getByLabelText(/Slackメッセージ取得日数/i)
    await user.clear(slackDaysInput)
    await user.type(slackDaysInput, '14')

    const saveButton = screen.getByRole('button', { name: /参照設定を保存/i })
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockUpdateAgent).toHaveBeenCalledWith('agent-1', expect.objectContaining({ slack_message_days: 14 }))
    })
  })

  it('should validate transcript_count range (0-10)', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    const transcriptInput = screen.getByLabelText(/トランスクリプト参照件数/i)
    await user.clear(transcriptInput)
    await user.type(transcriptInput, '11')

    await waitFor(() => {
      expect(screen.getByText(/0〜10の範囲で入力してください/i)).toBeInTheDocument()
    })
  })

  it('should validate slack_message_days range (1-30)', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    const slackDaysInput = screen.getByLabelText(/Slackメッセージ取得日数/i)
    await user.clear(slackDaysInput)
    await user.type(slackDaysInput, '0')

    await waitFor(() => {
      expect(screen.getByText(/1〜30の範囲で入力してください/i)).toBeInTheDocument()
    })
  })

  it('should disable save button when validation error exists', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />, { wrapper: createWrapper() })

    await openSettingsModal(user)

    const transcriptInput = screen.getByLabelText(/トランスクリプト参照件数/i)
    await user.clear(transcriptInput)
    await user.type(transcriptInput, '15')

    const saveButton = screen.getByRole('button', { name: /参照設定を保存/i })
    expect(saveButton).toBeDisabled()
  })
})
