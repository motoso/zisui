#!/usr/bin/env python3
"""
BookOrganizerのテスト
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from book_organizer.main import BookOrganizer


class TestBookOrganizer:
    """BookOrganizerクラスのテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行されるセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """各テストメソッドの後に実行されるクリーンアップ"""
        shutil.rmtree(self.temp_dir)

    def create_test_files(self, files):
        """テスト用ファイルを作成するヘルパーメソッド"""
        created_files = []
        for filename in files:
            file_path = self.temp_path / filename
            file_path.touch()
            created_files.append(file_path)
        return created_files

    def test_init(self):
        """初期化のテスト"""
        organizer = BookOrganizer(self.temp_dir)
        assert organizer.target_dir.resolve() == self.temp_path.resolve()
        assert organizer.dry_run is False
        assert organizer.auto is False
        assert organizer.create_cbz is False
        assert organizer.title == self.temp_path.name

    def test_init_with_options(self):
        """オプション付き初期化のテスト"""
        organizer = BookOrganizer(
            self.temp_dir, dry_run=True, auto=True, create_cbz=True
        )
        assert organizer.dry_run is True
        assert organizer.auto is True
        assert organizer.create_cbz is True

    def test_analyze_files_no_directory(self):
        """存在しないディレクトリのテスト"""
        non_existent_dir = self.temp_path / "non_existent"
        organizer = BookOrganizer(str(non_existent_dir))

        with pytest.raises(FileNotFoundError):
            organizer.analyze_files()

    def test_analyze_files_no_images(self):
        """画像ファイルがない場合のテスト"""
        # テキストファイルを作成
        (self.temp_path / "test.txt").touch()

        organizer = BookOrganizer(self.temp_dir)

        with pytest.raises(ValueError, match="画像ファイルが見つかりません"):
            organizer.analyze_files()

    def test_analyze_files_basic_case(self):
        """基本的なファイル分析のテスト"""
        # テスト用ファイルを作成
        files = [
            "manga.jpg",  # タイトルのみ
            "manga_001.jpg",  # 連番1
            "manga_002.jpg",  # 連番2
            "manga_003.jpg",  # 連番3
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        result = organizer.analyze_files()

        assert "manga" in result
        assert result["manga"]["title_only"] is not None
        assert result["manga"]["title_only"].name == "manga.jpg"
        assert len(result["manga"]["numbered"]) == 3
        assert result["manga"]["numbered"][0].name == "manga_001.jpg"
        assert result["manga"]["numbered"][1].name == "manga_002.jpg"
        assert result["manga"]["numbered"][2].name == "manga_003.jpg"

    def test_analyze_files_multiple_titles(self):
        """複数タイトルのテスト"""
        files = [
            "manga1.jpg",
            "manga1_001.jpg",
            "manga1_002.jpg",
            "manga2.png",
            "manga2_001.png",
            "manga2_002.png",
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        result = organizer.analyze_files()

        assert len(result) == 2
        assert "manga1" in result
        assert "manga2" in result

    def test_analyze_files_numbered_only(self):
        """連番ファイルのみの場合のテスト"""
        files = [
            "manga_001.jpg",
            "manga_002.jpg",
            "manga_003.jpg",
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        result = organizer.analyze_files()

        assert "manga" in result
        assert result["manga"]["title_only"] is None
        assert len(result["manga"]["numbered"]) == 3

    def test_natural_sort_key(self):
        """自然順序ソートのテスト"""
        organizer = BookOrganizer(self.temp_dir)

        # 数値順序のテスト
        key1 = organizer._natural_sort_key("file_001.jpg")
        key2 = organizer._natural_sort_key("file_002.jpg")
        key10 = organizer._natural_sort_key("file_010.jpg")

        assert key1 < key2 < key10

    def test_generate_rename_plan_insufficient_files(self):
        """ファイル数不足のテスト"""
        files = [
            "manga_001.jpg",  # 連番が1つだけ
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)

        with pytest.raises(ValueError, match="連番ファイルが2つ以上必要です"):
            organizer.generate_rename_plan()

    def test_generate_rename_plan_basic_case(self):
        """基本的なリネームプランのテスト"""
        files = [
            "manga.jpg",  # タイトル -> 002
            "manga_001.jpg",  # -> 003 (このファイルは表紙より前なので003になる)
            "manga_002.jpg",  # -> 001 (表紙、最後から2番目のファイル)
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        plan = organizer.generate_rename_plan()

        # プランの内容を確認
        assert len(plan) == 3

        # 表紙ファイル（manga_001.jpg が表紙になる、最後から2番目）
        # ソートされた状態で: [manga_001.jpg, manga_002.jpg]
        # 最後から2番目は manga_001.jpg なので、これが001になる
        cover_plan = next((p for p in plan if p[0].name == "manga_001.jpg"), None)
        assert cover_plan is not None
        assert "manga_001.jpg" in str(cover_plan[1])

        # タイトルファイル（manga.jpg -> manga_002）
        title_plan = next((p for p in plan if p[0].name == "manga.jpg"), None)
        assert title_plan is not None
        assert "manga_002.jpg" in str(title_plan[1])

        # 最後のファイル（manga_002.jpg -> manga_003）
        numbered_plan = next((p for p in plan if p[0].name == "manga_002.jpg"), None)
        assert numbered_plan is not None
        assert "manga_003.jpg" in str(numbered_plan[1])

    def test_generate_rename_plan_without_title_file(self):
        """タイトルファイルなしのテスト"""
        files = [
            "manga_001.jpg",  # -> 001 (表紙、最後から2番目)
            "manga_002.jpg",  # -> 002 (最後のファイル)
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        plan = organizer.generate_rename_plan()

        # プランの内容を確認
        assert len(plan) == 2

        # 表紙ファイル（manga_001.jpg -> manga_001、最後から2番目）
        cover_plan = next((p for p in plan if p[0].name == "manga_001.jpg"), None)
        assert cover_plan is not None
        assert "manga_001.jpg" in str(cover_plan[1])

        # 最後のファイル（manga_002.jpg -> manga_002）
        numbered_plan = next((p for p in plan if p[0].name == "manga_002.jpg"), None)
        assert numbered_plan is not None
        assert "manga_002.jpg" in str(numbered_plan[1])

    def test_preview_changes(self):
        """プレビュー機能のテスト"""
        files = [
            "manga.jpg",
            "manga_001.jpg",
            "manga_002.jpg",
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)

        # 標準出力をキャプチャしてテスト
        with patch("builtins.print") as mock_print:
            plan = organizer.preview_changes()

            # printが呼ばれたことを確認
            assert mock_print.called

            # プランが返されることを確認
            assert len(plan) == 3

    def test_execute_rename_dry_run(self):
        """ドライランのテスト"""
        files = [
            "manga.jpg",
            "manga_001.jpg",
            "manga_002.jpg",
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir, dry_run=True)
        plan = organizer.generate_rename_plan()

        with patch("builtins.print") as mock_print:
            result = organizer.execute_rename(plan)

            # ドライランメッセージが表示されることを確認
            mock_print.assert_any_call(
                "🔍 ドライランモード - 実際のファイル変更は行いません"
            )
            assert result is True

            # ファイルが実際には移動されていないことを確認
            assert (self.temp_path / "manga.jpg").exists()
            assert (self.temp_path / "manga_001.jpg").exists()
            assert (self.temp_path / "manga_002.jpg").exists()

    def test_magazine_mode_init(self):
        """雑誌モード初期化のテスト"""
        organizer = BookOrganizer(self.temp_dir, magazine_mode=True)
        assert organizer.magazine_mode is True

    def test_generate_rename_plan_magazine_mode(self):
        """雑誌モードでのリネームプランのテスト"""
        files = [
            "manga.jpg",  # タイトル -> 001
            "manga_001.jpg",  # -> 002
            "manga_002.jpg",  # -> 003
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir, magazine_mode=True)
        plan = organizer.generate_rename_plan()

        # 雑誌モードでは表紙なしで連番のみ
        assert len(plan) == 3

        # タイトルファイルが001になる
        title_plan = next((p for p in plan if p[0].name == "manga.jpg"), None)
        assert title_plan is not None
        assert "manga_001.jpg" in str(title_plan[1])

        # 連番ファイルが順番通りになる
        numbered_plan_1 = next((p for p in plan if p[0].name == "manga_001.jpg"), None)
        assert numbered_plan_1 is not None
        assert "manga_002.jpg" in str(numbered_plan_1[1])

        numbered_plan_2 = next((p for p in plan if p[0].name == "manga_002.jpg"), None)
        assert numbered_plan_2 is not None
        assert "manga_003.jpg" in str(numbered_plan_2[1])

    def test_generate_rename_plan_magazine_mode_no_title(self):
        """雑誌モード・タイトルファイルなしのテスト"""
        files = [
            "manga_001.jpg",  # -> 001
            "manga_002.jpg",  # -> 002
            "manga_003.jpg",  # -> 003
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir, magazine_mode=True)
        plan = organizer.generate_rename_plan()

        # 雑誌モードでは単純に順番通り
        assert len(plan) == 3

        plan_1 = next((p for p in plan if p[0].name == "manga_001.jpg"), None)
        assert plan_1 is not None
        assert "manga_001.jpg" in str(plan_1[1])

        plan_2 = next((p for p in plan if p[0].name == "manga_002.jpg"), None)
        assert plan_2 is not None
        assert "manga_002.jpg" in str(plan_2[1])

        plan_3 = next((p for p in plan if p[0].name == "manga_003.jpg"), None)
        assert plan_3 is not None
        assert "manga_003.jpg" in str(plan_3[1])
