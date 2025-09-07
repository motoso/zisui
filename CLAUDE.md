## 開発環境

このプロジェクトは **uv** を使用して開発されています。

### テストの実行

```bash
# テストを実行
uv run pytest tests/ -v

# カバレッジ付きでテストを実行
uv run pytest tests/ -v --cov=book_organizer

# テスト依存関係のインストール
uv add --dev pytest pytest-cov
```

### リンタ・フォーマッタ

```bash
# 開発用ツールのインストール
uv add --dev black ruff

# コードフォーマット
uv run black src/ tests/

# リント
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/  # 自動修正
```

### 実行

```bash
# 開発版の実行
uv run book-organizer

# 特定のディレクトリで実行
uv run book-organizer /path/to/book

# ドライラン
uv run book-organizer --dry-run ./book

# 自動実行
uv run book-organizer --auto ./book
```

## 機能概要

### 既存機能

1. **ファイル分析**: 画像ファイル（jpg, jpeg, png）を分析し、タイトルと連番ファイルに分類
2. **リネーム計画**: ファイルを適切な順序（表紙、タイトル、本文）で整理する計画を生成
3. **ファイル実行**: 実際のファイル移動とディレクトリ作成を実行
4. **CBZ作成**: 整理後のディレクトリをCBZファイルに変換

## TDD開発プロセス

Kent BeckのTDDプロセスに従って開発：

1. **Red**: 失敗するテストを書く
2. **Green**: テストを通すための最小限のコードを書く
3. **Refactor**: コードをリファクタリングする

新機能追加時は必ずテストファーストで開発すること。

## コミット前チェックリスト

**必須**: コミット前に以下を実行すること

```bash
# 1. リント・フォーマットチェック
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# 2. 必要に応じてフォーマット適用
uv run ruff format src/ tests/

# 3. テスト実行
uv run pytest tests/ -v

# 4. カバレッジ付きテスト（CI と同じ）
uv run pytest tests/ -v --cov=book_organizer --cov-report=term-missing
```

**理由**: CIと同じチェックをローカルで行うことで、CI失敗を防ぐ