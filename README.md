# Book Organizer

本のスキャンファイルを適切な形式（表紙、001、002...）に自動整理するツール

## 機能

- **自動整理**: スキャンファイルを適切な順序で整理
- **表紙検出**: 表紙ファイルを自動識別
- **ドライラン**: 実際の変更前にプレビュー
- **CBZ作成**: 整理後にCBZファイルを作成

## インストール

```bash
# リポジトリのクローン
git clone <repository-url>
cd book-organizer

# 依存関係のインストール
uv sync
```

## 使用方法

```bash
# 基本的な使用
uv run book-organizer /path/to/book

# ドライランモード
uv run book-organizer --dry-run /path/to/book

# 自動実行モード
uv run book-organizer --auto /path/to/book

# CBZ作成
uv run book-organizer --create-cbz /path/to/book
```

## サポートファイル形式

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)

## 開発

### テスト実行

```bash
uv run pytest
```

### テストカバレッジ

```bash
uv run pytest --cov=book_organizer
```

