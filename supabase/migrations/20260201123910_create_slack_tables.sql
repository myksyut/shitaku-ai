-- Slack連携テーブル
-- slack_integrations: Slackワークスペース連携情報
-- slack_messages: 取得したSlackメッセージ

-- slack_integrations テーブル
CREATE TABLE public.slack_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workspace_id VARCHAR(50) NOT NULL,
    workspace_name VARCHAR(100) NOT NULL,
    encrypted_access_token TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, workspace_id)
);

CREATE INDEX idx_slack_integrations_user_id ON public.slack_integrations(user_id);

ALTER TABLE public.slack_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own slack integrations" ON public.slack_integrations
    FOR ALL USING (auth.uid() = user_id);

-- slack_messages テーブル
CREATE TABLE public.slack_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_id UUID NOT NULL REFERENCES public.slack_integrations(id) ON DELETE CASCADE,
    channel_id VARCHAR(50) NOT NULL,
    message_ts VARCHAR(50) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    text TEXT NOT NULL,
    posted_at TIMESTAMPTZ NOT NULL,
    UNIQUE(integration_id, channel_id, message_ts)
);

CREATE INDEX idx_slack_messages_integration_channel ON public.slack_messages(integration_id, channel_id);
CREATE INDEX idx_slack_messages_posted_at ON public.slack_messages(channel_id, posted_at);

ALTER TABLE public.slack_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own slack messages" ON public.slack_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.slack_integrations
            WHERE id = integration_id AND user_id = auth.uid()
        )
    );
