-- oauth_statesテーブルにredirect_originカラムを追加
-- OAuth callback後のリダイレクト先をstate毎に動的に決定するため
-- NULLable: 既存レコードとの互換性、および未指定時はフォールバック使用

ALTER TABLE public.oauth_states
    ADD COLUMN redirect_origin TEXT;
