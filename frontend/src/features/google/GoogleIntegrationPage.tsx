import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, Card } from '../../components/ui'
import { GoogleIcon } from '../../components/ui/GoogleIcon'
import {
  useDeleteGoogleIntegration,
  useGoogleIntegrations,
  useStartAdditionalScopes,
  useStartGoogleOAuth,
  useSyncRecurringMeetings,
} from './hooks'
import type { GoogleIntegration } from './types'

const SCOPE_LABELS: Record<string, string> = {
  'https://www.googleapis.com/auth/userinfo.email': 'メールアドレス',
  'https://www.googleapis.com/auth/userinfo.profile': 'プロフィール',
  'https://www.googleapis.com/auth/calendar.readonly': 'カレンダー（読み取り）',
  'https://www.googleapis.com/auth/calendar': 'カレンダー（読み書き）',
  'https://www.googleapis.com/auth/drive.readonly': 'Drive（読み取り）',
  'https://www.googleapis.com/auth/drive': 'Drive（読み書き）',
  'https://www.googleapis.com/auth/documents.readonly': 'ドキュメント（読み取り）',
  'https://www.googleapis.com/auth/documents': 'ドキュメント（読み書き）',
}

function getScopeLabel(scope: string): string {
  return SCOPE_LABELS[scope] || scope.split('/').pop() || scope
}

const TRANSCRIPT_SCOPES = [
  'https://www.googleapis.com/auth/drive.readonly',
  'https://www.googleapis.com/auth/documents.readonly',
]

function hasTranscriptScopes(grantedScopes: string[]): boolean {
  return TRANSCRIPT_SCOPES.every((scope) => grantedScopes.includes(scope))
}

function IntegrationItem({ integration }: { integration: GoogleIntegration }) {
  const deleteIntegration = useDeleteGoogleIntegration()
  const startAdditionalScopes = useStartAdditionalScopes()

  const handleDelete = () => {
    if (window.confirm(`${integration.email}との連携を解除しますか？`)) {
      deleteIntegration.mutate(integration.id)
    }
  }

  const handleRequestAdditionalScopes = () => {
    startAdditionalScopes.mutate(integration.id)
  }

  const needsTranscriptScopes = !hasTranscriptScopes(integration.granted_scopes)

  return (
    <Card style={{ marginBottom: 'var(--space-4)' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              background: '#fff',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            }}
          >
            <GoogleIcon size={28} />
          </div>
          <div>
            <h3
              style={{
                fontSize: 'var(--font-size-lg)',
                fontWeight: 700,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-1)',
              }}
            >
              {integration.email}
            </h3>
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              連携日: {new Date(integration.created_at).toLocaleDateString('ja-JP')}
            </span>
          </div>
        </div>
        <Button variant="ghost" onClick={handleDelete} disabled={deleteIntegration.isPending}>
          {deleteIntegration.isPending ? '解除中...' : '連携解除'}
        </Button>
      </div>

      <div style={{ marginTop: 'var(--space-4)' }}>
        <h4
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 600,
            color: 'var(--color-warm-gray-600)',
            marginBottom: 'var(--space-2)',
          }}
        >
          許可されたスコープ
          {integration.granted_scopes.length > 0 && (
            <span style={{ fontWeight: 400, marginLeft: 'var(--space-2)' }}>
              ({integration.granted_scopes.length}件)
            </span>
          )}
        </h4>
        {integration.granted_scopes.length > 0 ? (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 'var(--space-2)',
            }}
          >
            {integration.granted_scopes.map((scope) => (
              <span
                key={scope}
                style={{
                  display: 'inline-block',
                  padding: 'var(--space-1) var(--space-3)',
                  background: 'var(--color-cream-200)',
                  borderRadius: 'var(--radius-full)',
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-warm-gray-700)',
                }}
              >
                {getScopeLabel(scope)}
              </span>
            ))}
          </div>
        ) : (
          <span style={{ color: 'var(--color-warm-gray-500)', fontSize: 'var(--font-size-sm)' }}>
            スコープ情報がありません
          </span>
        )}
      </div>

      {needsTranscriptScopes && (
        <div
          style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-3)',
            background: 'var(--color-cream-100)',
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--space-3)',
          }}
        >
          <div>
            <p
              style={{
                fontSize: 'var(--font-size-sm)',
                fontWeight: 600,
                color: 'var(--color-warm-gray-700)',
                marginBottom: 'var(--space-1)',
              }}
            >
              トランスクリプト機能を有効にする
            </p>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              Google Drive・ドキュメントへのアクセス許可が必要です
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRequestAdditionalScopes}
            isLoading={startAdditionalScopes.isPending}
          >
            {startAdditionalScopes.isPending ? '処理中...' : '権限を追加'}
          </Button>
        </div>
      )}

      {startAdditionalScopes.isError && (
        <div
          style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'var(--color-error-50)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-error-600)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          追加権限の取得に失敗しました。再度お試しください。
        </div>
      )}
    </Card>
  )
}

export function GoogleIntegrationPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: integrations, isLoading, error } = useGoogleIntegrations()
  const startOAuth = useStartGoogleOAuth()
  const syncMeetings = useSyncRecurringMeetings()
  const hasSyncedRef = useRef(false)

  // OAuth成功後にカレンダー同期を自動実行
  useEffect(() => {
    const success = searchParams.get('success')
    if (success === 'true' && !hasSyncedRef.current) {
      hasSyncedRef.current = true
      syncMeetings.mutate(undefined, {
        onSettled: () => {
          // 同期完了後にURLパラメータをクリア
          setSearchParams({}, { replace: true })
        },
      })
    }
  }, [searchParams, setSearchParams, syncMeetings])

  const handleConnect = () => {
    startOAuth.mutate()
  }

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-8)' }}>
        <h1
          style={{
            fontSize: 'var(--font-size-2xl)',
            fontWeight: 800,
            color: 'var(--color-warm-gray-800)',
            marginBottom: 'var(--space-2)',
          }}
        >
          Google連携設定
        </h1>
        <p style={{ color: 'var(--color-warm-gray-500)' }}>
          GoogleアカウントとShitaku.aiを連携して、カレンダーやドキュメントからアジェンダを自動生成できます。
        </p>
      </div>

      {/* Connect Button */}
      <Card style={{ marginBottom: 'var(--space-6)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--space-4)',
          }}
        >
          <div>
            <h3
              style={{
                fontSize: 'var(--font-size-base)',
                fontWeight: 600,
                color: 'var(--color-warm-gray-800)',
                marginBottom: 'var(--space-1)',
              }}
            >
              新しいGoogleアカウントを連携
            </h3>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              Googleの認証画面に遷移します
            </p>
          </div>
          <Button
            variant="primary"
            onClick={handleConnect}
            isLoading={startOAuth.isPending}
            leftIcon={<GoogleIcon size={18} />}
          >
            Googleと連携
          </Button>
        </div>
        {startOAuth.isError && (
          <div
            style={{
              marginTop: 'var(--space-3)',
              padding: 'var(--space-3)',
              background: 'var(--color-error-50)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-error-600)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            連携の開始に失敗しました。再度お試しください。
          </div>
        )}
      </Card>

      {/* Connected Accounts */}
      <h2
        style={{
          fontSize: 'var(--font-size-lg)',
          fontWeight: 700,
          color: 'var(--color-warm-gray-800)',
          marginBottom: 'var(--space-4)',
        }}
      >
        連携済みアカウント
      </h2>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-warm-gray-500)' }}>
          読み込み中...
        </div>
      ) : error ? (
        <Card>
          <div style={{ textAlign: 'center', color: 'var(--color-error-600)' }}>連携情報の取得に失敗しました</div>
        </Card>
      ) : integrations && integrations.length > 0 ? (
        <div>
          {integrations.map((integration) => (
            <IntegrationItem key={integration.id} integration={integration} />
          ))}
        </div>
      ) : (
        <Card>
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--space-4)',
            }}
          >
            <div style={{ marginBottom: 'var(--space-3)' }}>
              <GoogleIcon size={48} />
            </div>
            <p style={{ color: 'var(--color-warm-gray-600)', marginBottom: 'var(--space-2)' }}>
              連携済みのアカウントはありません
            </p>
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-warm-gray-500)' }}>
              上のボタンからGoogleアカウントを連携してください
            </p>
          </div>
        </Card>
      )}
    </div>
  )
}
