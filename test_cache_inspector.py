#!/usr/bin/env python3
"""Unit tests for cache_inspector.py"""

import json
import os
import pickle
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cache_inspector import (
    calculate_md5,
    find_common_cache_locations,
    format_size,
    get_file_info,
    inspect_cache,
    inspect_json_file,
    inspect_pickle_file,
    inspect_sqlite_cache,
    scan_directory_cache,
)


class TestFormatSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(format_size(512), "512.00 B")

    def test_kilobytes(self):
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(2048), "2.00 KB")

    def test_megabytes(self):
        self.assertEqual(format_size(1024 * 1024), "1.00 MB")

    def test_gigabytes(self):
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.00 GB")

    def test_terabytes(self):
        self.assertEqual(format_size(1024 * 1024 * 1024 * 1024), "1.00 TB")

    def test_large_size(self):
        result = format_size(1024 * 1024 * 1024 * 1024 * 1024)
        self.assertIn("PB", result)


class TestCalculateMD5(unittest.TestCase):
    def test_md5_of_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            md5_hash = calculate_md5(temp_path)
            self.assertEqual(len(md5_hash), 32)
            self.assertTrue(all(c in "0123456789abcdef" for c in md5_hash))
        finally:
            os.unlink(temp_path)

    def test_md5_nonexistent_file(self):
        result = calculate_md5("/nonexistent/path/file.txt")
        self.assertEqual(result, "unreadable")


class TestGetFileInfo(unittest.TestCase):
    def test_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            info = get_file_info(temp_path)
            self.assertNotIn("error", info)
            self.assertIn("path", info)
            self.assertIn("size_bytes", info)
            self.assertEqual(info["size_bytes"], 4)
            self.assertIn("md5", info)
            self.assertTrue(info["is_file"])
            self.assertFalse(info["is_dir"])
        finally:
            os.unlink(temp_path)

    def test_nonexistent_file(self):
        info = get_file_info("/nonexistent/path/file.txt")
        self.assertIn("error", info)
        self.assertEqual(info["error"], "File not found")

    def test_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            info = get_file_info(temp_dir)
            self.assertNotIn("error", info)
            self.assertTrue(info["is_dir"])
            self.assertFalse(info["is_file"])


class TestInspectPickleFile(unittest.TestCase):
    def test_dict_pickle(self):
        data = {"key1": "value1", "key2": 42, "key3": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            pickle.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_pickle_file(temp_path)
            self.assertEqual(result["type"], "pickle")
            self.assertEqual(result["data_type"], "dict")
            self.assertEqual(result["item_count"], 3)
            self.assertIn("key1", result["top_level_keys"])
        finally:
            os.unlink(temp_path)

    def test_list_pickle(self):
        data = [1, 2, 3, 4, 5]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            pickle.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_pickle_file(temp_path)
            self.assertEqual(result["type"], "pickle")
            self.assertEqual(result["data_type"], "list")
            self.assertEqual(result["item_count"], 5)
        finally:
            os.unlink(temp_path)

    def test_nested_structure(self):
        data = {"outer": {"inner": {"deep": "value"}}}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            pickle.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_pickle_file(temp_path, unpack_nested=True, max_depth=5)
            self.assertIn("nested_structure", result)
        finally:
            os.unlink(temp_path)

    def test_invalid_pickle(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            f.write(b"not a pickle")
            temp_path = f.name

        try:
            result = inspect_pickle_file(temp_path)
            self.assertIn("error", result)
        finally:
            os.unlink(temp_path)


class TestInspectJSONFile(unittest.TestCase):
    def test_dict_json(self):
        data = {"name": "test", "count": 10, "items": ["a", "b", "c"]}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_json_file(temp_path)
            self.assertEqual(result["type"], "json")
            self.assertEqual(result["data_type"], "dict")
            self.assertEqual(result["item_count"], 3)
            self.assertIn("name", result["top_level_keys"])
        finally:
            os.unlink(temp_path)

    def test_list_json(self):
        data = [{"id": 1}, {"id": 2}, {"id": 3}]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_json_file(temp_path)
            self.assertEqual(result["type"], "json")
            self.assertEqual(result["data_type"], "list")
            self.assertEqual(result["item_count"], 3)
        finally:
            os.unlink(temp_path)

    def test_nested_structure(self):
        data = {"level1": {"level2": {"level3": "deep"}}}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_json_file(temp_path, unpack_nested=True, max_depth=5)
            self.assertIn("nested_structure", result)
        finally:
            os.unlink(temp_path)

    def test_invalid_json(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            f.write("not valid json")
            temp_path = f.name

        try:
            result = inspect_json_file(temp_path)
            self.assertIn("error", result)
        finally:
            os.unlink(temp_path)


class TestInspectSQLiteCache(unittest.TestCase):
    def test_single_table(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            temp_path = f.name

        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE users (id INTEGER, name TEXT)")
            cursor.execute("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
            conn.commit()
            conn.close()

            result = inspect_sqlite_cache(temp_path)
            self.assertEqual(result["type"], "sqlite")
            self.assertIn("users", result["tables"])
            self.assertEqual(result["table_info"]["users"]["row_count"], 2)
        finally:
            os.unlink(temp_path)

    def test_multiple_tables(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            temp_path = f.name

        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE table1 (id INTEGER)")
            cursor.execute("CREATE TABLE table2 (name TEXT)")
            conn.commit()
            conn.close()

            result = inspect_sqlite_cache(temp_path)
            self.assertEqual(len(result["tables"]), 2)
        finally:
            os.unlink(temp_path)

    def test_empty_database(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            temp_path = f.name

        try:
            sqlite3.connect(temp_path).close()
            result = inspect_sqlite_cache(temp_path)
            self.assertEqual(result["type"], "sqlite")
            self.assertEqual(result["tables"], [])
        finally:
            os.unlink(temp_path)


class TestScanDirectoryCache(unittest.TestCase):
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = scan_directory_cache(temp_dir)
            self.assertNotIn("error", result)
            self.assertEqual(result["total_files"], 0)
            self.assertEqual(result["total_dirs"], 0)

    def test_directory_with_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "file1.txt").write_text("content1")
            Path(temp_dir, "file2.json").write_text('{"key": "value"}')

            result = scan_directory_cache(temp_dir)
            self.assertEqual(result["total_files"], 2)
            self.assertEqual(result["file_types"][".txt"], 1)
            self.assertEqual(result["file_types"][".json"], 1)

    def test_directory_with_subdirs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir, "subdir")
            subdir.mkdir()
            Path(subdir, "nested.txt").write_text("nested content")

            result = scan_directory_cache(temp_dir, max_depth=3)
            self.assertEqual(result["total_files"], 1)
            self.assertEqual(result["total_dirs"], 1)

    def test_cache_files_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data = {"test": "data"}
            pkl_path = Path(temp_dir, "cache.pkl")
            with open(pkl_path, "wb") as f:
                pickle.dump(data, f)

            result = scan_directory_cache(temp_dir, unpack_nested=True)
            self.assertEqual(len(result["cache_files"]), 1)

    def test_nonexistent_directory(self):
        result = scan_directory_cache("/nonexistent/directory/path")
        self.assertIn("error", result)


class TestInspectCache(unittest.TestCase):
    def test_auto_detect_pickle(self):
        data = {"key": "value"}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            pickle.dump(data, f)
            temp_path = f.name

        try:
            result = inspect_cache(temp_path)
            self.assertEqual(result["type"], "pickle")
        finally:
            os.unlink(temp_path)

    def test_auto_detect_json(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            json.dump({"test": "data"}, f)
            temp_path = f.name

        try:
            result = inspect_cache(temp_path)
            self.assertEqual(result["type"], "json")
        finally:
            os.unlink(temp_path)

    def test_auto_detect_sqlite(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            temp_path = f.name

        try:
            sqlite3.connect(temp_path).close()
            result = inspect_cache(temp_path)
            self.assertEqual(result["type"], "sqlite")
        finally:
            os.unlink(temp_path)

    def test_force_type_pickle(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"dummy")
            temp_path = f.name

        try:
            result = inspect_cache(temp_path, cache_type="pickle")
            self.assertIn("error", result)
        finally:
            os.unlink(temp_path)

    def test_nonexistent_path(self):
        result = inspect_cache("/nonexistent/path/file.pkl")
        self.assertIn("error", result)

    def test_directory_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = inspect_cache(temp_dir)
            self.assertNotIn("error", result)
            self.assertIn("total_files", result)


class TestFindCommonCacheLocations(unittest.TestCase):
    def test_returns_list(self):
        locations = find_common_cache_locations()
        self.assertIsInstance(locations, list)

    def test_contains_valid_paths(self):
        locations = find_common_cache_locations()
        for loc in locations:
            self.assertTrue(Path(loc).exists())


if __name__ == "__main__":
    unittest.main()
