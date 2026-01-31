# Python テスト規約

## テストフレームワーク
- pytest を使用
- pytest-cov でカバレッジ測定
- pytest-asyncio で非同期テスト

## ディレクトリ構造
```
tests/
├── __init__.py
├── conftest.py          # 共通フィクスチャ
├── unit/                # 単体テスト
│   └── test_*.py
└── integration/         # 統合テスト
    └── test_*.py
```

## フィクスチャパターン

### データベースセッション
```python
@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
```

### テストクライアント
```python
@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

## テスト記述ルール

### 命名規則
- `test_<機能>_<シナリオ>` 形式
- 日本語コメントで目的を明記

```python
def test_create_user_with_valid_data():
    """有効なデータでユーザーを作成できること"""
    ...

def test_create_user_with_duplicate_email():
    """重複メールでエラーになること"""
    ...
```

### AAAパターン
```python
def test_example():
    # Arrange（準備）
    user_data = {"email": "test@example.com", "password": "password"}

    # Act（実行）
    response = client.post("/users/", json=user_data)

    # Assert（検証）
    assert response.status_code == 201
```

## カバレッジ要件
- 新規コード: 80%以上
- 重要なビジネスロジック: 90%以上

```bash
uv run pytest --cov=app --cov-report=term-missing
```
