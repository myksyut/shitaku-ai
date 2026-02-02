"""Google Docs API client for document operations.

Provides methods for retrieving document content from Google Docs.
Following ADR-0003 Google Workspace integration pattern.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Google Docs API endpoints
DOCS_API_BASE = "https://docs.googleapis.com/v1"


@dataclass
class DocsDocument:
    """Google Docsドキュメント情報."""

    document_id: str
    title: str
    body_text: str


class GoogleDocsClient:
    """Google Docs APIクライアント.

    Google Docsドキュメントのテキストコンテンツを取得する。
    """

    def __init__(self, access_token: str) -> None:
        """GoogleDocsClientを初期化する.

        Args:
            access_token: Google OAuth access token with documents.readonly scope.
        """
        if not access_token:
            raise ValueError("access_token is required")
        self._access_token = access_token

    async def get_document_content(self, document_id: str) -> DocsDocument | None:
        """ドキュメントIDでドキュメントコンテンツを取得する.

        Args:
            document_id: Google DocsのドキュメントID。

        Returns:
            DocsDocumentオブジェクト。見つからない場合はNone。

        Raises:
            ValueError: API呼び出しが失敗した場合。
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DOCS_API_BASE}/documents/{document_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error("Failed to get document: %s", error_msg)
                raise ValueError(f"Google Docs API error: {error_msg}")

            data = response.json()
            return self._to_docs_document(data)

    async def get_document_text(self, document_id: str) -> str | None:
        """ドキュメントIDでテキストコンテンツのみを取得する.

        Args:
            document_id: Google DocsのドキュメントID。

        Returns:
            ドキュメントのテキストコンテンツ。見つからない場合はNone。

        Raises:
            ValueError: API呼び出しが失敗した場合。
        """
        doc = await self.get_document_content(document_id)
        if doc is None:
            return None
        return doc.body_text

    def _to_docs_document(self, data: dict[str, object]) -> DocsDocument:
        """APIレスポンスをDocsDocumentに変換する.

        Args:
            data: Google Docs APIのドキュメントレスポンス。

        Returns:
            DocsDocumentオブジェクト。
        """
        document_id = str(data.get("documentId", ""))
        title = str(data.get("title", ""))
        body_text = self._extract_text_from_body(data.get("body", {}))

        return DocsDocument(
            document_id=document_id,
            title=title,
            body_text=body_text,
        )

    def _extract_text_from_body(self, body: object) -> str:
        """ドキュメントボディからテキストを抽出する.

        Google Docsのボディは複雑なネスト構造を持つため、
        再帰的にテキスト要素を抽出する。

        Args:
            body: Google Docs APIのbodyオブジェクト。

        Returns:
            抽出されたテキスト。
        """
        if not isinstance(body, dict):
            return ""

        text_parts: list[str] = []
        content = body.get("content", [])

        if not isinstance(content, list):
            return ""

        for element in content:
            if not isinstance(element, dict):
                continue
            text = self._extract_text_from_element(element)
            if text:
                text_parts.append(text)

        return "".join(text_parts)

    def _extract_text_from_element(self, element: dict[str, object]) -> str:
        """ドキュメント要素からテキストを抽出する.

        Args:
            element: Google Docs APIの要素オブジェクト。

        Returns:
            抽出されたテキスト。
        """
        text_parts: list[str] = []

        # Paragraph要素の処理
        text_parts.extend(self._extract_text_from_paragraph(element.get("paragraph")))

        # Table要素の処理
        text_parts.extend(self._extract_text_from_table(element.get("table")))

        return "".join(text_parts)

    def _extract_text_from_paragraph(self, paragraph: object) -> list[str]:
        """Paragraph要素からテキストを抽出する."""
        if not isinstance(paragraph, dict):
            return []

        text_parts: list[str] = []
        elements = paragraph.get("elements", [])
        if not isinstance(elements, list):
            return []

        for para_element in elements:
            if not isinstance(para_element, dict):
                continue
            text_run = para_element.get("textRun")
            if isinstance(text_run, dict):
                content = text_run.get("content")
                if isinstance(content, str):
                    text_parts.append(content)

        return text_parts

    def _extract_text_from_table(self, table: object) -> list[str]:
        """Table要素からテキストを抽出する."""
        if not isinstance(table, dict):
            return []

        text_parts: list[str] = []
        table_rows = table.get("tableRows", [])
        if not isinstance(table_rows, list):
            return []

        for row in table_rows:
            if not isinstance(row, dict):
                continue
            text_parts.extend(self._extract_text_from_table_row(row))

        return text_parts

    def _extract_text_from_table_row(self, row: dict[str, object]) -> list[str]:
        """テーブル行からテキストを抽出する."""
        text_parts: list[str] = []
        cells = row.get("tableCells", [])
        if not isinstance(cells, list):
            return []

        for cell in cells:
            if not isinstance(cell, dict):
                continue
            cell_content = cell.get("content", [])
            if isinstance(cell_content, list):
                text_parts.extend(
                    self._extract_text_from_element(cell_element)
                    for cell_element in cell_content
                    if isinstance(cell_element, dict)
                )

        return text_parts
