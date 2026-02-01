---
allowed-tools: Bash(gh issue view:*),Bash(gh search:*),Bash(gh issue list:*),Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh pr list:*),Bash(gh api:*),Bash(jq:*),WebFetch,WebSearch
description: 5つの観点 (品質、パフォーマンス、テスト、ドキュメント、セキュリティ) からPRを包括的にレビューする
argument-hint: [owner/repo] [pr-number]
---

REPO: $1
PR NUMBER: $2

## ステップ 1: プロジェクトルールの読み込み

最初に、プロジェクトルートの CLAUDE.md ファイルを Read ツールで読み込み、プロジェクト固有のルール、開発環境、設計方針を確認する。この情報は、後続のすべてのサブエージェントに共有される。

## ステップ 2: サブエージェントによる包括的レビュー

以下の主要領域についてサブエージェントを使用して包括的なコードレビューを実行する:

- code-quality-reviewer (コード品質レビュアー)
- performance-reviewer (パフォーマンスレビュアー)
- test-coverage-reviewer (テストカバレッジレビュアー)
- documentation-accuracy-reviewer (ドキュメント正確性レビュアー): 正確性検証 + 更新サジェスチョン生成
- security-code-reviewer (セキュリティコードレビュアー)

**重要**: 各サブエージェントには、ステップ1で読み込んだ CLAUDE.md の内容を前提知識として提供する。各エージェント内で CLAUDE.md を再読み込みする必要はない。

## ステップ 3: フィードバックの統合と投稿

- 各エージェントには注目すべきフィードバックのみを提供するよう指示する
- 具体的な問題については積極的にインラインコメントでフィードバックを提供する
- 全般的な所見や称賛にはトップレベルコメントを使用する
- Pull Request をマージしてよいか、修正が必要かどうかを明示的に示す
