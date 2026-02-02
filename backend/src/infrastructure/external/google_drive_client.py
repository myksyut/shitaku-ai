"""Google Drive API client for file operations.

Provides methods for searching and retrieving files from Google Drive.
Following ADR-0003 Google Workspace integration pattern.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# Google Drive API endpoints
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"

# Google Docs MIME type
GOOGLE_DOCS_MIME_TYPE = "application/vnd.google-apps.document"


@dataclass
class DriveFile:
    """Google Driveファイル情報."""

    id: str
    name: str
    mime_type: str
    created_time: datetime
    modified_time: datetime
    web_view_link: str | None


class GoogleDriveClient:
    """Google Drive APIクライアント.

    Meet Recordingsフォルダからトランスクリプトファイルを検索する。
    """

    def __init__(self, access_token: str) -> None:
        """GoogleDriveClientを初期化する.

        Args:
            access_token: Google OAuth access token with drive.readonly scope.
        """
        if not access_token:
            raise ValueError("access_token is required")
        self._access_token = access_token

    async def search_transcript_files(
        self,
        folder_name: str = "Meet Recordings",
        max_results: int = 100,
    ) -> list[DriveFile]:
        """Meet Recordingsフォルダからトランスクリプトファイルを検索する.

        Args:
            folder_name: 検索対象のフォルダ名。デフォルトは "Meet Recordings"。
            max_results: 取得する最大件数。

        Returns:
            DriveFileオブジェクトのリスト。

        Raises:
            ValueError: API呼び出しが失敗した場合。
        """
        # まずMeet Recordingsフォルダを検索
        folder_id = await self._find_folder_by_name(folder_name)
        if not folder_id:
            logger.info("Folder '%s' not found", folder_name)
            return []

        # フォルダ内のGoogle Docsを検索
        return await self._list_docs_in_folder(folder_id, max_results)

    async def get_file_by_id(self, file_id: str) -> DriveFile | None:
        """ファイルIDでファイル情報を取得する.

        Args:
            file_id: Google DriveのファイルID。

        Returns:
            DriveFileオブジェクト。見つからない場合はNone。

        Raises:
            ValueError: API呼び出しが失敗した場合。
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "fields": "id,name,mimeType,createdTime,modifiedTime,webViewLink",
                },
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error("Failed to get file: %s", error_msg)
                raise ValueError(f"Google Drive API error: {error_msg}")

            data = response.json()
            return self._to_drive_file(data)

    async def _find_folder_by_name(self, folder_name: str) -> str | None:
        """フォルダ名でフォルダIDを検索する.

        Args:
            folder_name: 検索するフォルダ名。

        Returns:
            フォルダID。見つからない場合はNone。
        """
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DRIVE_API_BASE}/files",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "q": query,
                    "fields": "files(id,name)",
                    "pageSize": 1,
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error("Failed to search folder: %s", error_msg)
                raise ValueError(f"Google Drive API error: {error_msg}")

            data = response.json()
            files = data.get("files", [])
            if files:
                return str(files[0]["id"])
            return None

    async def _list_docs_in_folder(self, folder_id: str, max_results: int) -> list[DriveFile]:
        """フォルダ内のGoogle Docsを一覧取得する.

        Args:
            folder_id: 検索対象のフォルダID。
            max_results: 取得する最大件数。

        Returns:
            DriveFileオブジェクトのリスト。
        """
        query = f"'{folder_id}' in parents and mimeType = '{GOOGLE_DOCS_MIME_TYPE}' and trashed = false"

        all_files: list[DriveFile] = []
        page_token: str | None = None

        async with httpx.AsyncClient() as client:
            while len(all_files) < max_results:
                params: dict[str, str | int] = {
                    "q": query,
                    "fields": "nextPageToken,files(id,name,mimeType,createdTime,modifiedTime,webViewLink)",
                    "pageSize": min(100, max_results - len(all_files)),
                    "orderBy": "createdTime desc",
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    f"{DRIVE_API_BASE}/files",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                    params=params,
                )

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error("Failed to list files: %s", error_msg)
                    raise ValueError(f"Google Drive API error: {error_msg}")

                data = response.json()
                files = data.get("files", [])
                all_files.extend(self._to_drive_file(f) for f in files)

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return all_files

    def _to_drive_file(self, data: dict[str, str]) -> DriveFile:
        """APIレスポンスをDriveFileに変換する.

        Args:
            data: Google Drive APIのファイルレスポンス。

        Returns:
            DriveFileオブジェクト。
        """
        return DriveFile(
            id=str(data["id"]),
            name=str(data["name"]),
            mime_type=str(data["mimeType"]),
            created_time=datetime.fromisoformat(str(data["createdTime"]).replace("Z", "+00:00")),
            modified_time=datetime.fromisoformat(str(data["modifiedTime"]).replace("Z", "+00:00")),
            web_view_link=data.get("webViewLink"),
        )
