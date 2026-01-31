# Python コーディング規約

## 基本原則

### 型ヒント
- すべての関数に型ヒントを付ける
- `Any`型の使用は禁止（`Unknown`または具体的な型を使用）
- `Optional[T]`より`T | None`を使用

```python
# Good
def get_user(user_id: int) -> User | None:
    ...

# Bad
def get_user(user_id):
    ...
```

### Pydantic
- データバリデーションにはPydanticを使用
- `model_config`で設定を定義
- `ConfigDict`を使用してattributeベースの設定

```python
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
```

### 非同期処理
- I/Oバウンドな処理は`async/await`を使用
- CPUバウンドな処理は同期関数で実装
- `asyncio.gather`で並列実行を最適化

## コードスタイル

### ruff設定
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "UP"]
```

### インポート順序
1. 標準ライブラリ
2. サードパーティ
3. ローカルモジュール

```python
import os
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
```

## 品質チェック
```bash
uv run ruff check .       # Lint
uv run ruff format .      # Format
uv run mypy .             # 型チェック
```
