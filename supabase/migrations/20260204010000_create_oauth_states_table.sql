-- OAuth State永続化テーブル
-- OAuth認証フローにおけるCSRF対策用stateを管理
-- サーバーレス環境でのインスタンス間state共有を実現

-- oauth_states テーブル
CREATE TABLE public.oauth_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('slack', 'google')),
    scopes TEXT[],
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '5 minutes'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_oauth_states_state ON public.oauth_states(state);
CREATE INDEX idx_oauth_states_expires_at ON public.oauth_states(expires_at);

-- RLSを有効化
ALTER TABLE public.oauth_states ENABLE ROW LEVEL SECURITY;

-- state作成は認証済みユーザーのみ（自分のstateのみ作成可能）
CREATE POLICY "Users can insert own states" ON public.oauth_states
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 自分のstateのみ読み取り可能
CREATE POLICY "Users can read own states" ON public.oauth_states
    FOR SELECT USING (auth.uid() = user_id);

-- 自分のstateのみ削除可能
CREATE POLICY "Users can delete own states" ON public.oauth_states
    FOR DELETE USING (auth.uid() = user_id);
