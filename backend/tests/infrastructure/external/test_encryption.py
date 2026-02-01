"""Encryption module tests."""

from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet, InvalidToken

from src.infrastructure.external.encryption import (
    decrypt_token,
    encrypt_token,
    generate_encryption_key,
    get_encryption_key,
)


class TestEncryption:
    """暗号化モジュールのテスト"""

    @pytest.fixture
    def valid_key(self) -> str:
        """有効な暗号化キーを生成"""
        return Fernet.generate_key().decode()

    def test_get_encryption_key_success(self, valid_key: str) -> None:
        """設定から暗号化キーを取得できる"""
        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = valid_key
            key = get_encryption_key()
            assert key == valid_key.encode()

    def test_get_encryption_key_not_set(self) -> None:
        """設定が未設定の場合はエラー"""
        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = None
            with pytest.raises(ValueError, match="SLACK_TOKEN_ENCRYPTION_KEY is not set"):
                get_encryption_key()

    def test_encrypt_decrypt_roundtrip(self, valid_key: str) -> None:
        """暗号化と復号が正しく動作する"""
        original_token = "xoxb-test-token-12345"

        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = valid_key
            encrypted = encrypt_token(original_token)
            decrypted = decrypt_token(encrypted)

            assert decrypted == original_token
            assert encrypted != original_token

    def test_encrypt_produces_different_ciphertext(self, valid_key: str) -> None:
        """同じ平文でも異なる暗号文が生成される（IV/nonceが異なるため）"""
        token = "xoxb-test-token"

        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = valid_key
            encrypted1 = encrypt_token(token)
            encrypted2 = encrypt_token(token)

            # Fernetは毎回異なる暗号文を生成
            assert encrypted1 != encrypted2

    def test_generate_encryption_key(self) -> None:
        """暗号化キーが正しく生成される"""
        key = generate_encryption_key()

        # Fernetキーとして有効か確認
        Fernet(key.encode())  # 無効なら例外が発生

    def test_decrypt_with_wrong_key_fails(self, valid_key: str) -> None:
        """異なるキーでは復号できない"""
        token = "xoxb-test-token"
        other_key = Fernet.generate_key().decode()

        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = valid_key
            encrypted = encrypt_token(token)

        with patch("src.infrastructure.external.encryption.settings") as mock_settings:
            mock_settings.SLACK_TOKEN_ENCRYPTION_KEY = other_key
            with pytest.raises(InvalidToken):
                decrypt_token(encrypted)
