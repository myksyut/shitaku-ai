"""Tests for NormalizationService domain types."""

import pytest

from src.domain.services.normalization_service import (
    NormalizationError,
    NormalizationResult,
    Replacement,
)


class TestReplacement:
    """Replacementデータクラスのテスト."""

    def test_replacement_creation(self) -> None:
        """Replacementが正しくインスタンス化できること."""
        replacement = Replacement(
            original="かなざわ",
            canonical="金沢太郎",
            start_pos=0,
            end_pos=4,
        )

        assert replacement.original == "かなざわ"
        assert replacement.canonical == "金沢太郎"
        assert replacement.start_pos == 0
        assert replacement.end_pos == 4


class TestNormalizationResult:
    """NormalizationResultデータクラスのテスト."""

    def test_normalization_result_creation(self) -> None:
        """NormalizationResultが正しくインスタンス化できること."""
        result = NormalizationResult(
            original_text="かなざわさんが発言",
            normalized_text="金沢太郎さんが発言",
            replacements=[
                Replacement(
                    original="かなざわ",
                    canonical="金沢太郎",
                    start_pos=0,
                    end_pos=4,
                )
            ],
        )

        assert result.original_text == "かなざわさんが発言"
        assert result.normalized_text == "金沢太郎さんが発言"
        assert len(result.replacements) == 1

    def test_replacement_count_returns_correct_count(self) -> None:
        """replacement_countが正しい件数を返すこと."""
        result = NormalizationResult(
            original_text="テスト",
            normalized_text="テスト",
            replacements=[
                Replacement(original="a", canonical="A", start_pos=0, end_pos=1),
                Replacement(original="b", canonical="B", start_pos=2, end_pos=3),
                Replacement(original="c", canonical="C", start_pos=4, end_pos=5),
            ],
        )

        assert result.replacement_count == 3

    def test_replacement_count_returns_zero_when_no_replacements(self) -> None:
        """置換がない場合はreplacement_countが0を返すこと."""
        result = NormalizationResult(
            original_text="変更なし",
            normalized_text="変更なし",
            replacements=[],
        )

        assert result.replacement_count == 0


class TestNormalizationError:
    """NormalizationErrorのテスト."""

    def test_normalization_error_is_exception(self) -> None:
        """NormalizationErrorがExceptionを継承していること."""
        error = NormalizationError("テストエラー")
        assert isinstance(error, Exception)
        assert str(error) == "テストエラー"

    def test_normalization_error_can_be_raised(self) -> None:
        """NormalizationErrorがraiseできること."""
        with pytest.raises(NormalizationError) as exc_info:
            raise NormalizationError("LLM API Error")

        assert "LLM API Error" in str(exc_info.value)
