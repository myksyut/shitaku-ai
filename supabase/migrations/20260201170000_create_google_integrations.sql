-- Google Workspace連携テーブル
-- google_integrations: Googleアカウント連携情報

-- google_integrations テーブル
CREATE TABLE public.google_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    granted_scopes TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, email)
);

CREATE INDEX idx_google_integrations_user_id ON public.google_integrations(user_id);

ALTER TABLE public.google_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own google integrations" ON public.google_integrations
    FOR ALL USING (auth.uid() = user_id);
