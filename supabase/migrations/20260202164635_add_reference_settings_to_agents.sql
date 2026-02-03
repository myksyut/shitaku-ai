-- agentsテーブルに参照設定カラムを追加
-- transcript_count: アジェンダ生成時に参照するトランスクリプト件数
-- slack_message_days: Slackメッセージ取得日数

ALTER TABLE agents
ADD COLUMN transcript_count INTEGER NOT NULL DEFAULT 3,
ADD COLUMN slack_message_days INTEGER NOT NULL DEFAULT 7;

-- バリデーション制約
ALTER TABLE agents
ADD CONSTRAINT chk_transcript_count CHECK (transcript_count >= 0 AND transcript_count <= 10),
ADD CONSTRAINT chk_slack_message_days CHECK (slack_message_days >= 1 AND slack_message_days <= 30);

-- コメント追加（ドキュメント目的）
COMMENT ON COLUMN agents.transcript_count IS 'アジェンダ生成時に参照するトランスクリプト件数（0-10）';
COMMENT ON COLUMN agents.slack_message_days IS 'Slackメッセージ取得日数（1-30）';
