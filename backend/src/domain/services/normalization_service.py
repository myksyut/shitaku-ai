"""NormalizationService interface for domain layer.

Abstract base class defining the contract for text normalization operations.
Implementations should be provided in the infrastructure layer (using LLM).
Following ADR-0001 clean architecture principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.dictionary_entry import DictionaryEntry


@dataclass
class Replacement:
    """テキストの置換情報.

    Attributes:
        original: 元の表記
        canonical: 正式名称（置換後）
        start_pos: 元テキストでの開始位置
        end_pos: 元テキストでの終了位置
    """

    original: str
    canonical: str
    start_pos: int
    end_pos: int


@dataclass
class NormalizationResult:
    """正規化結果.

    Attributes:
        original_text: 正規化前のテキスト
        normalized_text: 正規化後のテキスト
        replacements: 置換情報のリスト
    """

    original_text: str
    normalized_text: str
    replacements: list[Replacement]

    @property
    def replacement_count(self) -> int:
        """置換された箇所の数を返す."""
        return len(self.replacements)


class NormalizationError(Exception):
    """正規化処理のエラー.

    LLM呼び出し失敗やレスポンスのパースエラー時に発生。
    """


class NormalizationService(ABC):
    """議事録テキストを正規化するドメインサービスのインターフェース.

    ユビキタス言語辞書を参照して、テキスト内の表記揺れを正式名称に置換する。
    実際のLLM呼び出しはインフラ層で実装する。
    """

    @abstractmethod
    def normalize(
        self,
        text: str,
        dictionary: list[DictionaryEntry],
    ) -> NormalizationResult:
        """テキストを辞書を参照して正規化する.

        Args:
            text: 正規化対象のテキスト
            dictionary: 参照する辞書エントリのリスト

        Returns:
            正規化結果（元テキスト、正規化後テキスト、置換情報）

        Raises:
            NormalizationError: 正規化処理に失敗した場合
        """
