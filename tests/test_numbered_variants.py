#!/usr/bin/env python3
"""
番号バリエーション機能のテスト
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from book_organizer.main import BookOrganizer


class TestNumberedVariants:
    """番号バリエーション機能のテストクラス"""

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

    def test_analyze_files_with_numbered_variants(self):
        """000_1, 000_2のような番号バリエーションファイルの分析テスト"""
        files = [
            "manga_000.jpg",    # 000
            "manga_000_1.jpg",  # 000のバリエーション1
            "manga_000_2.jpg",  # 000のバリエーション2
            "manga_001.jpg",    # 001
            "manga_002.jpg",    # 002
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        result = organizer.analyze_files()

        # すべてのバリエーションが認識されるべき
        assert "manga" in result
        assert len(result["manga"]["numbered"]) == 5

        # ソート後の順序を確認
        numbered_names = [f.name for f in result["manga"]["numbered"]]
        expected_order = [
            "manga_000.jpg",
            "manga_000_1.jpg",
            "manga_000_2.jpg",
            "manga_001.jpg",
            "manga_002.jpg",
        ]
        assert numbered_names == expected_order

    def test_generate_rename_plan_with_numbered_variants(self):
        """000_1, 000_2のような番号バリエーションファイルのリネームプランテスト"""
        files = [
            "manga_000.jpg",    # -> 002 (最初のファイル)
            "manga_000_1.jpg",  # -> 003 (000のバリエーション1、000の次)
            "manga_000_2.jpg",  # -> 004 (000のバリエーション2、000_1の次)
            "manga_001.jpg",    # -> 001 (表紙、最後から2番目)
            "manga_002.jpg",    # -> 005 (最後のファイル)
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        plan = organizer.generate_rename_plan()

        # プランの内容を確認
        assert len(plan) == 5

        # 表紙ファイル（manga_001.jpg -> manga_001）
        cover_plan = next((p for p in plan if p[0].name == "manga_001.jpg"), None)
        assert cover_plan is not None
        assert "manga_001.jpg" in str(cover_plan[1])

        # 000が002になる（タイトルの次）
        plan_000 = next((p for p in plan if p[0].name == "manga_000.jpg"), None)
        assert plan_000 is not None
        assert "manga_002.jpg" in str(plan_000[1])

        # 000_1が003になる（000の次）
        plan_000_1 = next((p for p in plan if p[0].name == "manga_000_1.jpg"), None)
        assert plan_000_1 is not None
        assert "manga_003.jpg" in str(plan_000_1[1])

        # 000_2が004になる（000_1の次）
        plan_000_2 = next((p for p in plan if p[0].name == "manga_000_2.jpg"), None)
        assert plan_000_2 is not None
        assert "manga_004.jpg" in str(plan_000_2[1])

        # 最後のファイル（manga_002.jpg -> manga_005）
        last_plan = next((p for p in plan if p[0].name == "manga_002.jpg"), None)
        assert last_plan is not None
        assert "manga_005.jpg" in str(last_plan[1])

    def test_basic_functionality(self):
        """基本機能のテスト"""
        files = [
            "manga_001.jpg",
            "manga_002.jpg",
        ]
        self.create_test_files(files)

        organizer = BookOrganizer(self.temp_dir)
        result = organizer.analyze_files()

        assert "manga" in result
        assert len(result["manga"]["numbered"]) == 2