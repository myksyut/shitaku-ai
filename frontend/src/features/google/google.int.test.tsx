// Google Integration Test - Design Doc: google-workspace-integration
// Generated: 2026-02-02 | Task: P2-10
/**
 * Google連携機能のフロントエンド統合テスト
 *
 * テスト対象: RecurringMeetingList コンポーネント
 * - AC5: 定例MTG一覧表示
 * - AC9: エージェント作成画面遷移
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { RecurringMeetingList } from './RecurringMeetingList'
import type { GoogleIntegration, RecurringMeetingsResponse } from './types'

// Mock supabase
vi.mock('../../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      signOut: vi.fn(),
    },
  },
}))

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const mockIntegrations: GoogleIntegration[] = [
  {
    id: 'integration-1',
    email: 'test@example.com',
    granted_scopes: ['https://www.googleapis.com/auth/calendar.readonly'],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  },
]

const mockMeetingsResponse: RecurringMeetingsResponse = {
  meetings: [
    {
      id: 'meeting-1',
      google_event_id: 'event_1',
      title: 'Weekly Standup',
      frequency: 'weekly',
      attendees: ['user1@example.com', 'user2@example.com'],
      next_occurrence: '2026-02-08T10:00:00Z',
      agent_id: null,
    },
    {
      id: 'meeting-2',
      google_event_id: 'event_2',
      title: 'Monthly Review',
      frequency: 'monthly',
      attendees: ['user1@example.com', 'user3@example.com', 'user4@example.com'],
      next_occurrence: '2026-03-01T14:00:00Z',
      agent_id: null,
    },
  ],
}

const server = setupServer(
  http.get(`${API_BASE_URL}/api/v1/google/integrations`, () => {
    return HttpResponse.json(mockIntegrations)
  }),
  http.get(`${API_BASE_URL}/api/v1/google/calendar/recurring`, () => {
    return HttpResponse.json(mockMeetingsResponse)
  }),
  http.post(`${API_BASE_URL}/api/v1/google/calendar/recurring/sync`, () => {
    return HttpResponse.json({ created: 2, updated: 0 })
  }),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient()
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('Google Calendar Integration Test', () => {
  const mockOnCreateAgent = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // AC: "定例MTG一覧画面でCalendar連携イベントが表示される"
  // ROI: 56 | ビジネス価値: 8 | 頻度: 7
  // 振る舞い: 画面表示 -> API呼び出し -> 定例MTG一覧表示
  // @category: core-functionality
  // @dependency: RecurringMeetingList, useGoogleIntegrations, useRecurringMeetings
  // @complexity: medium
  //
  // 検証項目:
  // - 定例MTGタイトルが表示される
  // - 頻度が日本語で表示される（毎週、月次）
  // - 参加者数が表示される
  // - 次回日程が表示される
  describe('AC5: 定例MTG一覧画面でCalendar連携イベントが表示される', () => {
    it('定例MTG一覧が正しく表示される', async () => {
      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      // 定例MTGタイトルが表示される
      await waitFor(() => {
        expect(screen.getByText('Weekly Standup')).toBeInTheDocument()
        expect(screen.getByText('Monthly Review')).toBeInTheDocument()
      })

      // 頻度の表示を確認
      expect(screen.getByText('毎週')).toBeInTheDocument()
      expect(screen.getByText('月次')).toBeInTheDocument()

      // 参加者数の表示を確認
      expect(screen.getByText(/参加者: 2人/)).toBeInTheDocument()
      expect(screen.getByText(/参加者: 3人/)).toBeInTheDocument()
    })

    it('Google連携がない場合は連携メッセージが表示される', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/google/integrations`, () => {
          return HttpResponse.json([])
        }),
      )

      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      await waitFor(() => {
        expect(screen.getByText(/Google連携が必要です/)).toBeInTheDocument()
      })
    })

    it('定例MTGがない場合は空メッセージが表示される', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/google/calendar/recurring`, () => {
          return HttpResponse.json({ meetings: [] })
        }),
      )

      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      await waitFor(() => {
        expect(screen.getByText(/定例MTGが見つかりません/)).toBeInTheDocument()
      })
    })
  })

  // AC: "定例MTG選択でエージェント作成画面に遷移しプリセットされる"
  // ROI: 48 | ビジネス価値: 8 | 頻度: 6
  // 振る舞い: エージェント作成ボタンクリック -> onCreateAgentコールバック呼び出し
  // @category: core-functionality
  // @dependency: RecurringMeetingList, MeetingCard, onCreateAgent callback
  // @complexity: low
  //
  // 検証項目:
  // - エージェント作成ボタンが表示される
  // - クリックでonCreateAgentが正しい引数で呼び出される
  // - 連携済みの場合はボタンではなくラベルが表示される
  describe('AC9: 定例MTG選択でエージェント作成画面に遷移しプリセットされる', () => {
    it('エージェント作成ボタンクリックでonCreateAgentが呼び出される', async () => {
      const user = userEvent.setup()

      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      // ボタンが表示されるまで待機
      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: 'エージェント作成' })).toHaveLength(2)
      })

      // 最初のエージェント作成ボタンをクリック
      const createButtons = screen.getAllByRole('button', { name: 'エージェント作成' })
      await user.click(createButtons[0])

      // onCreateAgentが正しい引数で呼び出される
      expect(mockOnCreateAgent).toHaveBeenCalledWith('meeting-1', 'Weekly Standup', [
        'user1@example.com',
        'user2@example.com',
      ])
    })

    it('エージェント連携済みの場合はラベルが表示される', async () => {
      const meetingsWithAgent: RecurringMeetingsResponse = {
        meetings: [
          {
            id: 'meeting-1',
            google_event_id: 'event_1',
            title: 'Weekly Standup',
            frequency: 'weekly',
            attendees: ['user1@example.com', 'user2@example.com'],
            next_occurrence: '2026-02-08T10:00:00Z',
            agent_id: 'agent-1', // 連携済み
          },
        ],
      }

      server.use(
        http.get(`${API_BASE_URL}/api/v1/google/calendar/recurring`, () => {
          return HttpResponse.json(meetingsWithAgent)
        }),
      )

      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      await waitFor(() => {
        expect(screen.getByText('エージェント連携済み')).toBeInTheDocument()
      })

      // エージェント作成ボタンは表示されない
      expect(screen.queryByRole('button', { name: 'エージェント作成' })).not.toBeInTheDocument()
    })
  })

  // 同期機能のテスト
  describe('同期機能', () => {
    it('同期ボタンクリックで同期が実行される', async () => {
      const user = userEvent.setup()

      renderWithProviders(<RecurringMeetingList onCreateAgent={mockOnCreateAgent} />)

      // 同期ボタンが表示されるまで待機
      await waitFor(() => {
        expect(screen.getByRole('button', { name: '同期' })).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: '同期' }))

      // 同期完了メッセージが表示される
      await waitFor(() => {
        expect(screen.getByText(/同期完了: 2件作成, 0件更新/)).toBeInTheDocument()
      })
    })
  })
})
