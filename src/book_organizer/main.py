#!/usr/bin/env python3
"""
本ファイル整理ツール - Book Organizer

本のスキャンファイルを適切な形式（表紙、001、002...）に自動整理するツール
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict


class BookOrganizer:
    """本ファイル整理クラス"""

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    NUMBERED_FILE_PATTERN = r"_\d+(?:_\d+)?$"

    def __init__(
        self,
        target_dir: str,
        dry_run: bool = False,
        auto: bool = False,
        create_cbz: bool = False,
        magazine_mode: bool = False,
    ):
        self.target_dir = Path(target_dir).resolve()
        self.dry_run = dry_run
        self.auto = auto
        self.create_cbz = create_cbz
        self.magazine_mode = magazine_mode
        self.title = self.target_dir.name

    def analyze_files(self) -> Dict[str, Dict]:
        """ファイルを分析して複数のファイル群に分類する

        Returns:
            Dict[str, Dict]: {タイトル: {'title_only': PathまたはNone, 'numbered': [Path]}}
        """
        if not self.target_dir.exists():
            raise FileNotFoundError(f"ディレクトリが見つかりません: {self.target_dir}")

        # 画像ファイルを取得
        all_files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            all_files.extend(self.target_dir.glob(f"*{ext}"))

        if not all_files:
            raise ValueError("画像ファイルが見つかりません")

        # ファイル群を分類
        file_groups = defaultdict(lambda: {"title_only": None, "numbered": []})

        for file_path in all_files:
            stem = file_path.stem

            # 連番ファイルかチェック（_数字で終わるか、_数字_数字で終わる）
            if re.search(self.NUMBERED_FILE_PATTERN, stem):
                # タイトル部分を抽出
                title = re.sub(self.NUMBERED_FILE_PATTERN, "", stem)
                file_groups[title]["numbered"].append(file_path)
            else:
                # タイトルのみファイル
                file_groups[stem]["title_only"] = file_path

        # 各グループの連番ファイルをソート
        for title in file_groups:
            file_groups[title]["numbered"].sort(
                key=lambda x: self._natural_sort_key(x.name)
            )

        # 空のグループを除去
        return {
            title: files
            for title, files in file_groups.items()
            if files["title_only"] or files["numbered"]
        }

    def _natural_sort_key(self, filename: str):
        """自然順序ソート用のキー生成"""
        return [
            int(text) if text.isdigit() else text.lower()
            for text in re.split(r"(\d+)", filename)
        ]

    def generate_rename_plan(self) -> List[Tuple[Path, Path, str]]:
        """リネーム計画を生成する

        Returns:
            List[Tuple[Path, Path, str]]: (現在のファイル, 新しいファイルパス, タイトル) のリスト
        """
        file_groups = self.analyze_files()
        rename_plan = []

        if not file_groups:
            raise ValueError("有効なファイル群が見つかりません")

        for title, files in file_groups.items():
            title_only_file = files["title_only"]
            numbered_files = files["numbered"]

            if not numbered_files:
                # 連番ファイルがない場合はスキップ
                continue

            # 雑誌モードでは連番ファイル数の制限を緩和
            if not self.magazine_mode and len(numbered_files) < 2:
                raise ValueError(f"タイトル '{title}': 連番ファイルが2つ以上必要です")

            # タイトル用ディレクトリのパス
            title_dir = self.target_dir / title

            if self.magazine_mode:
                # 雑誌モード: 表紙なしで単純に連番
                current_num = 1

                # タイトルファイルを001に
                if title_only_file:
                    title_new_name = title_dir / f"{title}_001{title_only_file.suffix}"
                    rename_plan.append((title_only_file, title_new_name, title))
                    current_num = 2

                # 連番ファイルを順番に
                for numbered_file in numbered_files:
                    new_name = (
                        title_dir / f"{title}_{current_num:03d}{numbered_file.suffix}"
                    )
                    rename_plan.append((numbered_file, new_name, title))
                    current_num += 1
            else:
                # 従来モード: 表紙あり
                # 表紙ファイル（最後から-1の連番ファイル）を001に
                cover_file = numbered_files[-2]  # 最後から-1のファイルが表紙
                cover_new_name = title_dir / f"{title}_001{cover_file.suffix}"
                rename_plan.append((cover_file, cover_new_name, title))

                # タイトルのみファイルを002に（表紙の次のページ）
                if title_only_file:
                    title_new_name = title_dir / f"{title}_002{title_only_file.suffix}"
                    rename_plan.append((title_only_file, title_new_name, title))

                # 既存の連番ファイルを調整
                start_num = (
                    3 if title_only_file else 2
                )  # タイトルファイルがある場合は003から、ない場合は002から

                for i, current_file in enumerate(numbered_files):
                    if current_file == cover_file:  # 表紙になるファイルはスキップ
                        continue

                    if i < len(numbered_files) - 2:  # 表紙より前のファイル
                        new_num = i + start_num
                        new_name = (
                            title_dir / f"{title}_{new_num:03d}{current_file.suffix}"
                        )
                        rename_plan.append((current_file, new_name, title))
                    else:  # 最後のファイル（元の027など）
                        # 表紙より前のファイル数を計算して適切な番号を付ける
                        files_before_cover = len(numbered_files) - 2
                        new_num = files_before_cover + start_num
                        new_name = (
                            title_dir / f"{title}_{new_num:03d}{current_file.suffix}"
                        )
                        rename_plan.append((current_file, new_name, title))

        return rename_plan

    def preview_changes(self):
        """変更内容をプレビュー表示"""
        try:
            file_groups = self.analyze_files()
            rename_plan = self.generate_rename_plan()

            print("📚 本ファイル整理ツール")
            print("=" * 50)
            print(f"対象: {self.target_dir}")
            print(f"検出されたファイル群: {len(file_groups)}個")
            print()

            print("現在のファイル構成:")
            for title, files in file_groups.items():
                print(f"  タイトル: {title}")
                if files["title_only"]:
                    print(f"    タイトルのみ: {files['title_only'].name}")
                if files["numbered"]:
                    print(f"    連番: {[f.name for f in files['numbered']]}")
            print()

            print("処理予定:")
            current_title = None
            for old_file, new_file, title in rename_plan:
                if current_title != title:
                    print(f"  ディレクトリ '{title}/' を作成:")
                    current_title = title
                relative_path = new_file.relative_to(self.target_dir)
                print(f"    {old_file.name} → {relative_path}")
            print()

            return rename_plan

        except Exception as e:
            print(f"❌ エラー: {e}")
            return []

    def execute_rename(self, rename_plan: List[Tuple[Path, Path, str]]) -> bool:
        """リネームとファイル移動を実行

        Args:
            rename_plan: リネーム計画

        Returns:
            bool: 成功したかどうか
        """
        if self.dry_run:
            print("🔍 ドライランモード - 実際のファイル変更は行いません")
            return True

        # 作成するディレクトリの一覧を作成
        directories_to_create = set()
        for _, new_file, _ in rename_plan:
            directories_to_create.add(new_file.parent)

        temp_files = []
        created_dirs = []

        try:
            # Step 1: ディレクトリを作成
            for dir_path in directories_to_create:
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_path)
                    print(f"📁 ディレクトリ作成: {dir_path.name}")

            # Step 2: 全ファイルを一時名に変更
            for i, (old_file, new_file, _) in enumerate(rename_plan):
                temp_name = old_file.parent / f"TEMP_RENAME_{i:03d}{old_file.suffix}"
                old_file.rename(temp_name)
                temp_files.append((temp_name, new_file))

            # Step 3: 一時ファイルを最終位置に移動
            for temp_file, new_file in temp_files:
                temp_file.rename(new_file)

            print("✅ ファイル整理が完了しました")

            # CBZファイル作成が有効な場合
            if self.create_cbz:
                self.create_cbz_files(created_dirs)

            return True

        except Exception as e:
            # エラー時は一時ファイルを元に戻す
            print(f"❌ エラーが発生しました: {e}")
            for i, (temp_file, _) in enumerate(temp_files):
                if temp_file.exists():
                    original_file = rename_plan[i][0]
                    temp_file.rename(original_file)

            # 作成したディレクトリを削除（空の場合のみ）
            for dir_path in created_dirs:
                try:
                    if dir_path.exists() and not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except OSError as cleanup_error:
                    # クリーンアップ失敗時はユーザーに対処方法を案内
                    print(f"⚠️  空のディレクトリを削除できませんでした: {dir_path}")
                    print(f"    原因: {cleanup_error}")
                    print("    対処法:")
                    print("      1. ファイルマネージャーで手動削除")
                    print(f"      2. ターミナル: rm -rf '{dir_path}' (Mac/Linux)")
                    print(
                        f"      3. コマンドプロンプト: rmdir /s '{dir_path}' (Windows)"
                    )
                    print(
                        "    注意: このディレクトリが残っていても次回実行には影響ありません"
                    )
            return False

    def run(self) -> bool:
        """メイン処理を実行"""
        rename_plan = self.preview_changes()

        if not rename_plan:
            return False

        # 確認または自動実行
        if not self.auto and not self.dry_run:
            response = input("この処理を実行しますか？ [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("処理をキャンセルしました")
                return False

        return self.execute_rename(rename_plan)

    def create_cbz_files(self, directories: List[Path]):
        """作成されたディレクトリをCBZファイルに変換"""
        for directory in directories:
            if not directory.exists() or not directory.is_dir():
                continue

            # 画像ファイルを取得してソート
            image_files = []
            for ext in self.SUPPORTED_EXTENSIONS:
                image_files.extend(directory.glob(f"*{ext}"))

            if not image_files:
                print(f"⚠️  {directory.name}: 画像ファイルが見つかりません")
                continue

            image_files.sort(key=lambda x: self._natural_sort_key(x.name))

            # CBZファイル作成
            cbz_path = directory.with_suffix(".cbz")
            if self.dry_run:
                print(f"🔍 [Dry Run] CBZ作成予定: {cbz_path.name}")
                continue

            try:
                with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as cbz:
                    for image_file in image_files:
                        cbz.write(image_file, image_file.name)

                print(f"📦 CBZ作成: {cbz_path.name} ({len(image_files)}枚)")
            except Exception as e:
                print(f"❌ CBZ作成エラー: {directory.name} - {e}")

    @staticmethod
    def convert_directory_to_cbz(directory_path: str, dry_run: bool = False) -> bool:
        """既存のディレクトリをCBZファイルに変換"""
        directory = Path(directory_path).resolve()

        if not directory.exists() or not directory.is_dir():
            print(f"❌ ディレクトリが見つかりません: {directory}")
            return False

        # 画像ファイルを取得
        image_files = []
        supported_extensions = {".jpg", ".jpeg", ".png"}

        for ext in supported_extensions:
            image_files.extend(directory.glob(f"*{ext}"))

        if not image_files:
            print(f"❌ 画像ファイルが見つかりません: {directory}")
            return False

        # 自然順序でソート
        image_files.sort(
            key=lambda x: [
                int(text) if text.isdigit() else text.lower()
                for text in re.split(r"(\d+)", x.name)
            ]
        )

        cbz_path = directory.with_suffix(".cbz")

        if dry_run:
            print(f"🔍 [Dry Run] CBZ作成予定: {cbz_path.name} ({len(image_files)}枚)")
            for img in image_files:
                print(f"    - {img.name}")
            return True

        try:
            with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as cbz:
                for image_file in image_files:
                    cbz.write(image_file, image_file.name)

            print(f"✅ CBZ作成完了: {cbz_path.name} ({len(image_files)}枚)")
            return True

        except Exception as e:
            print(f"❌ CBZ作成エラー: {e}")
            return False


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="本のスキャンファイルを適切な形式に自動整理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  book-organizer                         # 現在のディレクトリで実行
  book-organizer /path/to/book           # 指定ディレクトリで実行
  book-organizer --dry-run ./book        # プレビューのみ（実行しない）
  book-organizer --auto ./book           # 確認なしで自動実行
  book-organizer --cbz ./book            # 整理後にCBZファイルを作成
  book-organizer --magazine ./magazine   # 雑誌切り抜きモード
  book-organizer --to-cbz ./manga_dir    # 指定ディレクトリをCBZに変換
        """,
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="整理対象のディレクトリ (デフォルト: 現在のディレクトリ)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="プレビューのみで実際のファイル変更は行わない",
    )

    parser.add_argument("--auto", action="store_true", help="確認なしで自動実行")

    parser.add_argument("--cbz", action="store_true", help="整理後にCBZファイルを作成")

    parser.add_argument(
        "--to-cbz", metavar="DIRECTORY", help="指定したディレクトリをCBZファイルに変換"
    )

    parser.add_argument(
        "--magazine",
        action="store_true",
        help="雑誌切り抜きモード（裏表紙なしで最初から連番）",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()

    try:
        # --to-cbz オプションが指定された場合はディレクトリ変換のみ実行
        if args.to_cbz:
            success = BookOrganizer.convert_directory_to_cbz(
                args.to_cbz, dry_run=args.dry_run
            )
            sys.exit(0 if success else 1)

        # 通常の整理処理
        organizer = BookOrganizer(
            target_dir=args.directory,
            dry_run=args.dry_run,
            auto=args.auto,
            create_cbz=args.cbz,
            magazine_mode=args.magazine,
        )

        success = organizer.run()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
