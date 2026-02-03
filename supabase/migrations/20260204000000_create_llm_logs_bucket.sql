-- Create llm-logs storage bucket for LLM input/output logging
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'llm-logs',
    'llm-logs',
    false,
    10485760,  -- 10MB limit per file
    ARRAY['application/json']
)
ON CONFLICT (id) DO NOTHING;

-- RLS policy: Only service role can access (no user access needed)
-- The bucket is private and accessed only via service key from backend
