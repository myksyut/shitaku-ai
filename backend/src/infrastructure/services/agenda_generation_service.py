"""Agenda generation service using Claude.

Infrastructure service for generating meeting agendas.
"""

import logging
from dataclasses import dataclass, field

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.entities.knowledge import Knowledge
from src.domain.entities.meeting_transcript import MeetingTranscript
from src.infrastructure.external.bedrock_client import invoke_claude
from src.infrastructure.external.slack_client import SlackMessageData

logger = logging.getLogger(__name__)


@dataclass
class AgendaGenerationInput:
    """アジェンダ生成の入力."""

    latest_knowledge: Knowledge | None
    slack_messages: list[SlackMessageData]
    dictionary: list[DictionaryEntry]
    transcripts: list[MeetingTranscript] = field(default_factory=list)


class AgendaGenerationService:
    """アジェンダ生成サービス."""

    async def generate(self, input_data: AgendaGenerationInput) -> str:
        """アジェンダを生成する.

        Args:
            input_data: アジェンダ生成に必要な入力データ

        Returns:
            生成されたアジェンダのマークダウンテキスト

        Raises:
            Exception: LLM呼び出しに失敗した場合
        """
        prompt = self._build_prompt(input_data)

        try:
            result = invoke_claude(prompt, max_tokens=8192)
            if result is None:
                raise RuntimeError("LLM returned None")
            return result
        except Exception as e:
            logger.error("Agenda generation failed: %s", e)
            raise

    def _build_prompt(self, input_data: AgendaGenerationInput) -> str:
        """アジェンダ生成用のプロンプトを構築する.

        Args:
            input_data: アジェンダ生成に必要な入力データ

        Returns:
            構築されたプロンプト文字列
        """
        parts: list[str] = []

        # 辞書情報
        if input_data.dictionary:
            dict_info = "\n".join([f"- {e.canonical_name}" for e in input_data.dictionary])
            parts.append(f"## 参考: ユビキタス言語辞書\n{dict_info}")

        # ナレッジ
        if input_data.latest_knowledge:
            parts.append(f"## 過去のナレッジ\n{input_data.latest_knowledge.normalized_text}")

        # Slackメッセージ
        if input_data.slack_messages:
            messages = "\n".join(
                [
                    f"[{m.posted_at.strftime('%m/%d %H:%M')}] {m.user_name}: {m.text}"
                    for m in input_data.slack_messages[:50]  # 最大50件
                ]
            )
            parts.append(f"## 前回MTG以降のSlack履歴\n{messages}")

        # トランスクリプト情報
        if input_data.transcripts:
            transcript_entries: list[str] = []
            for transcript in input_data.transcripts:
                meeting_title = transcript.recurring_meeting_title or "不明な定例"
                meeting_date = transcript.meeting_date.strftime("%Y/%m/%d")
                # 内容が長い場合は最初の2000文字に切り詰め
                content = transcript.raw_text[:2000] if len(transcript.raw_text) > 2000 else transcript.raw_text
                transcript_entries.append(f"### {meeting_title} ({meeting_date})\n{content}")
            parts.append("## 過去のMTGトランスクリプト\n" + "\n\n".join(transcript_entries))

        context = "\n\n".join(parts)

        # データソースの状況を判定
        has_knowledge = input_data.latest_knowledge is not None
        has_slack = len(input_data.slack_messages) > 0

        if has_knowledge and has_slack:
            source_note = "ナレッジとSlack履歴の両方を参照しています。"
        elif has_knowledge:
            source_note = "ナレッジのみを参照しています（Slack履歴なし）。"
        elif has_slack:
            source_note = "Slack履歴のみを参照しています（ナレッジなし）。"
        else:
            source_note = "参照できる情報がありません。一般的なアジェンダ形式で生成してください。"

        return f"""あなたはMTGのアジェンダを作成するアシスタントです。

<meeting_philosophy>
会議の本質は「意思決定」と「合意形成」です。
意思決定には「判断材料」が必要です。
判断材料はMTG前に準備し、MTGは「決める」ことに集中します。
</meeting_philosophy>

<input>
## 前回議事録/ナレッジ
{context}

## 注意
- {source_note}
</input>

<extraction_focus>
MTGで扱うべき「未決事項」を抽出する際、以下も同時に特定してください：

1. **決めるために必要な情報は何か**
2. **その情報を誰が持っているか/調べられるか**
3. **MTG前に準備可能か、MTG中に共有するしかないか**
</extraction_focus>

<output_format>
## Part 1: 事前準備タスク

MTG **前** に完了すべきタスクを、担当者・期限付きで列挙。
期限は原則MTGの24時間前。

| 担当 | 準備内容 | 議題との関連 | 期限 |
|------|---------|-------------|------|
| ... | ... | ... | ... |

準備が完了していないと議論できない議題は、その旨を明記。

---

## Part 2: アジェンダ

### [議題名]（X分）

**【決めること】**
このMTGで決定・合意すべき具体的な問い

**【前提となる準備】**
- □ [準備タスク名]（担当者）← Part 1と紐付け

**【選択肢】**（わかっていれば）
- A案: ...
- B案: ...

**【決定者/合意者】**
最終判断を下す人
</output_format>

<guidelines>
- 準備タスクは「MTG中に初めて話す」を減らすためのもの
- 準備に1時間以上かかるものは、そもそも今回のMTGで扱うべきか再検討
- Slackで事前に共有できるものは「MTG前にSlackで共有」と指示
- 準備担当者は、その情報に最も近い人をアサイン
- 辞書にある用語は正式名称を使用
</guidelines>
"""
