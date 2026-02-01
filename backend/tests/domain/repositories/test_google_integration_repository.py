"""GoogleIntegrationRepository interface tests."""

import inspect
from abc import ABC

import pytest

from src.domain.repositories.google_integration_repository import (
    GoogleIntegrationRepository,
)


class TestGoogleIntegrationRepositoryInterface:
    """GoogleIntegrationRepositoryインターフェースのテスト"""

    def test_is_abstract_class(self) -> None:
        """GoogleIntegrationRepositoryは抽象クラスである"""
        assert issubclass(GoogleIntegrationRepository, ABC)

    def test_cannot_instantiate_directly(self) -> None:
        """抽象クラスは直接インスタンス化できない"""
        with pytest.raises(TypeError):
            GoogleIntegrationRepository()  # type: ignore[abstract]

    def test_has_create_method(self) -> None:
        """createメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "create")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.create)

    def test_has_get_by_id_method(self) -> None:
        """get_by_idメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "get_by_id")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.get_by_id)

    def test_has_get_by_email_method(self) -> None:
        """get_by_emailメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "get_by_email")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.get_by_email)

    def test_has_get_all_method(self) -> None:
        """get_allメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "get_all")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.get_all)

    def test_has_update_method(self) -> None:
        """updateメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "update")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.update)

    def test_has_delete_method(self) -> None:
        """deleteメソッドが定義されている"""
        assert hasattr(GoogleIntegrationRepository, "delete")
        assert inspect.iscoroutinefunction(GoogleIntegrationRepository.delete)
