// Slack Integration Test - Design Doc: mvp-core-features.md
// Generated: 2026-01-31 | Quota: 3/3 integration, 0/2 E2E
/**
 * Slack連携機能のフロントエンド統合テスト
 *
 * テスト対象: F4 Slack連携
 * - OAuth連携ボタンとリダイレクト
 * - 連携済みワークスペース表示
 * - チャンネル選択
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HttpResponse, http } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { SlackSettingsPage } from './SlackSettingsPage'

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

const mockIntegrations = [
  {
    id: 'integration-1',
    workspace_id: 'W12345',
    workspace_name: 'Test Workspace',
    created_at: '2026-01-31T10:00:00Z',
  },
]

const mockChannels = [
  { id: 'C001', name: 'general' },
  { id: 'C002', name: 'random' },
]

const server = setupServer(
  http.get(`${API_BASE_URL}/api/v1/slack/integrations`, () => {
    return HttpResponse.json(mockIntegrations)
  }),
  http.get(`${API_BASE_URL}/api/v1/slack/integrations/:id/channels`, () => {
    return HttpResponse.json(mockChannels)
  }),
  http.get(`${API_BASE_URL}/api/v1/slack/auth`, () => {
    return HttpResponse.json({ authorize_url: 'https://slack.com/oauth/v2/authorize?state=test' })
  }),
  http.delete(`${API_BASE_URL}/api/v1/slack/integrations/:id`, () => {
    return new HttpResponse(null, { status: 204 })
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

describe('Slack Integration Test', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // AC: "When ユーザーがSlack連携ボタンをクリックすると、
  //      システムは一意のstateパラメータを生成しセッションに保存した上で、
  //      Slack OAuth画面にリダイレクトする"
  // ROI: 48/11 = 4.4 | ビジネス価値: 8 | 頻度: 5
  // 振る舞い: 連携ボタンクリック -> API呼び出し -> Slack OAuth URLへリダイレクト
  // @category: core-functionality
  // @dependency: SlackConnectButton, useSlackAuth hook, API Client
  // @complexity: low
  //
  // 検証項目:
  // - 連携ボタンクリックでAPI呼び出しが実行される
  // - Slack OAuth URLへのリダイレクトが発生する
  // - リダイレクト前にローディング状態が表示される
  it('AC1: Slack連携ボタンでOAuth画面にリダイレクトされる', async () => {
    const user = userEvent.setup()
    const originalLocation = window.location
    const mockLocation = { ...originalLocation, href: '' }
    Object.defineProperty(window, 'location', {
      value: mockLocation,
      writable: true,
    })

    renderWithProviders(<SlackSettingsPage />)

    // ボタンが表示されるまで待機
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Slackワークスペースを連携/i })).toBeInTheDocument()
    })

    const connectButton = screen.getByRole('button', { name: /Slackワークスペースを連携/i })
    await user.click(connectButton)

    await waitFor(() => {
      expect(mockLocation.href).toBe('https://slack.com/oauth/v2/authorize?state=test')
    })

    Object.defineProperty(window, 'location', { value: originalLocation, writable: true })
  })

  // AC: "When ユーザーがSlack連携設定画面を開くと、
  //      システムは連携済みワークスペースとチャンネル一覧を表示する"
  // ROI: (implied) | ビジネス価値: 7 | 頻度: 6
  // 振る舞い: 設定画面開く -> API呼び出し -> ワークスペース+チャンネル表示
  // @category: core-functionality
  // @dependency: SlackSettings, WorkspaceList, ChannelList, useSlackIntegrations hook
  // @complexity: medium
  //
  // 検証項目:
  // - 画面表示時に連携一覧API呼び出しが実行される
  // - 連携済みワークスペースが表示される
  // - チャンネル一覧が表示される
  // - 未連携時は「連携なし」メッセージ表示
  it('AC4: Slack連携設定画面でワークスペースとチャンネル一覧が表示される', async () => {
    renderWithProviders(<SlackSettingsPage />)

    // ワークスペースが表示される
    await waitFor(() => {
      expect(screen.getByText('Test Workspace')).toBeInTheDocument()
    })

    // チャンネル一覧が表示される
    await waitFor(() => {
      expect(screen.getByText('#general')).toBeInTheDocument()
      expect(screen.getByText('#random')).toBeInTheDocument()
    })
  })

  it('AC4-alt: 未連携時は連携なしメッセージが表示される', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api/v1/slack/integrations`, () => {
        return HttpResponse.json([])
      }),
    )

    renderWithProviders(<SlackSettingsPage />)

    await waitFor(() => {
      expect(screen.getByText(/連携済みのワークスペースはありません/)).toBeInTheDocument()
    })
  })

  // AC: "When ユーザーがエージェントにSlackチャンネルを紐付けると、
  //      システムは紐付け情報をDBに保存する"
  // ROI: (implied) | ビジネス価値: 8 | 頻度: 5
  // 振る舞い: チャンネル選択 -> 保存 -> API呼び出し -> 紐付け完了表示
  // @category: core-functionality
  // @dependency: ChannelSelector, useUpdateAgent hook, API Client
  // @complexity: low
  //
  // 検証項目:
  // - チャンネル選択でAPI呼び出しが実行される
  // - 成功後、紐付け状態が更新される
  // - エージェント詳細に選択チャンネルが表示される
  it.todo('AC5: エージェントにSlackチャンネルを紐付けて保存できる')
  // Note: エージェント機能との統合が必要なため、別タスクで実装予定
})
