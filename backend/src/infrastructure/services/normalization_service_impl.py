"""NormalizationService implementation using Bedrock Claude.

Infrastructure layer implementation of NormalizationService interface.
Following ADR-0001 clean architecture principles.
"""

import json
import logging

from src.domain.entities.dictionary_entry import DictionaryEntry
from src.domain.services.normalization_service import (
    NormalizationError,
    NormalizationResult,
    NormalizationService,
    Replacement,
)
from src.infrastructure.external.bedrock_client import invoke_claude

logger = logging.getLogger(__name__)


class NormalizationServiceImpl(NormalizationService):
    """Bedrock Claudeを使用した正規化サービスの実装."""

    def normalize(
        self,
        text: str,
        dictionary: list[DictionaryEntry],
    ) -> NormalizationResult:
        """テキストを辞書を参照して正規化する."""
        if not dictionary:
            # 辞書が空の場合は正規化しない
            return NormalizationResult(
                original_text=text,
                normalized_text=text,
                replacements=[],
            )

        prompt = self._build_prompt(text, dictionary)

        try:
            response = invoke_claude(prompt, max_tokens=2048)
            if response is None:
                raise NormalizationError("LLM API returned None")

            return self._parse_response(text, response)

        except NormalizationError:
            raise
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            raise NormalizationError(f"Normalization failed: {e}") from e

    def _build_prompt(self, text: str, dictionary: list[DictionaryEntry]) -> str:
        """正規化用のプロンプトを構築する."""
        dict_entries = [
            {
                "canonical_name": entry.canonical_name,
                "description": entry.description or "",
            }
            for entry in dictionary
        ]

        dict_json = json.dumps(dict_entries, ensure_ascii=False, indent=2)

        return f"""以下の議事録テキストを、辞書を参照して正規化してください。

## 辞書
{dict_json}

## 議事録テキスト
{text}

## 指示
1. 辞書にある正式名称（canonical_name）と類似した表記を見つけたら、正式名称に置換してください
2. description（説明）を参考に、文脈を考慮して適切に判断してください
3. 辞書にない単語は変更しないでください
4. 結果をJSON形式で返してください

## 出力形式
{{
  "normalized_text": "正規化後のテキスト",
  "replacements": [
    {{"original": "元の表記", "canonical": "正式名称", "start_pos": 開始位置, "end_pos": 終了位置}},
    ...
  ]
}}

JSONのみを返してください。説明は不要です。"""

    def _parse_response(self, original_text: str, response: str) -> NormalizationResult:
        """LLMのレスポンスをパースする."""
        try:
            # JSONを抽出（```json ... ``` で囲まれている場合も対応）
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                parts = response.split("```")
                if len(parts) >= 2:
                    json_str = parts[1]

            data = json.loads(json_str.strip())

            replacements = [
                Replacement(
                    original=str(r.get("original", "")),
                    canonical=str(r.get("canonical", "")),
                    start_pos=int(r.get("start_pos", 0)),
                    end_pos=int(r.get("end_pos", 0)),
                )
                for r in data.get("replacements", [])
            ]

            return NormalizationResult(
                original_text=original_text,
                normalized_text=str(data.get("normalized_text", original_text)),
                replacements=replacements,
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            # パースに失敗した場合は元テキストをそのまま返す
            return NormalizationResult(
                original_text=original_text,
                normalized_text=original_text,
                replacements=[],
            )
