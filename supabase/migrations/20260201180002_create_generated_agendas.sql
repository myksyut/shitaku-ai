-- generated_agendas テーブル
-- 自動生成されたアジェンダを保存

CREATE TABLE public.generated_agendas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recurring_meeting_id UUID NOT NULL REFERENCES public.recurring_meetings(id) ON DELETE CASCADE,
    target_date TIMESTAMPTZ NOT NULL,
    agenda_content JSONB NOT NULL,
    sources JSONB NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'reviewed')),
    delivered_via TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- RLSポリシー（親テーブル経由でuser_id検証）
ALTER TABLE public.generated_agendas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own generated agendas" ON public.generated_agendas
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.recurring_meetings rm
            WHERE rm.id = generated_agendas.recurring_meeting_id
            AND rm.user_id = auth.uid()
        )
    );

-- インデックス
CREATE INDEX idx_generated_agendas_recurring_meeting_id ON public.generated_agendas(recurring_meeting_id);
CREATE INDEX idx_generated_agendas_target_date ON public.generated_agendas(target_date);
