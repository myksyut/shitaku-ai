-- Create dictionary_entries table for ubiquitous language dictionary
CREATE TABLE IF NOT EXISTS public.dictionary_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    canonical_name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    UNIQUE(user_id, canonical_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_dictionary_entries_user_id ON public.dictionary_entries(user_id);

-- Enable Row Level Security
ALTER TABLE public.dictionary_entries ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can manage their own dictionary entries
CREATE POLICY "Users can view own dictionary entries" ON public.dictionary_entries
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own dictionary entries" ON public.dictionary_entries
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own dictionary entries" ON public.dictionary_entries
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own dictionary entries" ON public.dictionary_entries
    FOR DELETE USING (auth.uid() = user_id);
