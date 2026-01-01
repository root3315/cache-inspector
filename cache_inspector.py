#!/usr/bin/env python3
"""
Cache Inspector - Tool to inspect and debug cache contents
Supports filesystem caches, pickle files, JSON caches, and more.
"""

import argparse
import hashlib
import json
import os
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get detailed file information including size, timestamps, and hash."""
    path = Path(filepath)
    if not path.exists():
        return {"error": "File not found"}
    
    stat = path.stat()
    return {
        "path": str(path.absolute()),
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        "md5": calculate_md5(filepath),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def calculate_md5(filepath: str) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (IOError, PermissionError):
        return "unreadable"


def _unpack_nested_data(data: Any, depth: int, max_depth: int) -> Dict[str, Any]:
    """Recursively unpack nested cache structures."""
    if depth >= max_depth:
        return {"type": type(data).__name__, "value": str(data)[:200], "truncated": True}

    result: Dict[str, Any] = {"type": type(data).__name__}

    if isinstance(data, dict):
        result["item_count"] = len(data)
        result["children"] = {}
        for key, value in list(data.items())[:10]:
            result["children"][str(key)] = _unpack_nested_data(value, depth + 1, max_depth)
    elif isinstance(data, (list, tuple)):
        result["item_count"] = len(data)
        result["children"] = []
        for i, item in enumerate(list(data)[:10]):
            result["children"].append(_unpack_nested_data(item, depth + 1, max_depth))
    elif isinstance(data, set):
        result["item_count"] = len(data)
        result["children"] = [_unpack_nested_data(item, depth + 1, max_depth) for item in list(data)[:10]]
    elif isinstance(data, bytes):
        result["value"] = f"<bytes: {len(data)} bytes>"
    elif isinstance(data, (str, int, float, bool, type(None))):
        result["value"] = str(data)[:200]
    else:
        result["value"] = str(data)[:200]

    return result


def inspect_pickle_file(filepath: str, unpack_nested: bool = False, max_depth: int = 3) -> Dict[str, Any]:
    """Load and inspect a pickle cache file."""
    try:
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        result: Dict[str, Any] = {
            "type": "pickle",
            "data_type": str(type(data).__name__),
            "top_level_keys": None,
            "item_count": None,
            "sample_data": None,
        }

        if isinstance(data, dict):
            result["top_level_keys"] = list(data.keys())[:20]
            result["item_count"] = len(data)
            if unpack_nested:
                result["nested_structure"] = _unpack_nested_data(data, 0, max_depth)
            else:
                result["sample_data"] = {k: str(v)[:100] for k, v in list(data.items())[:5]}
        elif isinstance(data, (list, tuple, set)):
            result["item_count"] = len(data)
            if unpack_nested:
                result["nested_structure"] = _unpack_nested_data(data, 0, max_depth)
            else:
                result["sample_data"] = [str(item)[:100] for item in list(data)[:5]]
        else:
            result["sample_data"] = str(data)[:500]

        return result
    except Exception as e:
        return {"error": f"Failed to load pickle: {str(e)}"}


def inspect_json_file(filepath: str, unpack_nested: bool = False, max_depth: int = 3) -> Dict[str, Any]:
    """Load and inspect a JSON cache file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        result: Dict[str, Any] = {
            "type": "json",
            "data_type": str(type(data).__name__),
            "top_level_keys": None,
            "item_count": None,
            "sample_data": None,
        }

        if isinstance(data, dict):
            result["top_level_keys"] = list(data.keys())[:20]
            result["item_count"] = len(data)
            if unpack_nested:
                result["nested_structure"] = _unpack_nested_data(data, 0, max_depth)
            else:
                result["sample_data"] = {k: str(v)[:100] for k, v in list(data.items())[:5]}
        elif isinstance(data, list):
            result["item_count"] = len(data)
            if unpack_nested:
                result["nested_structure"] = _unpack_nested_data(data, 0, max_depth)
            else:
                result["sample_data"] = [str(item)[:100] for item in data[:5]]
        else:
            result["sample_data"] = str(data)[:500]

        return result
    except Exception as e:
        return {"error": f"Failed to load JSON: {str(e)}"}


def inspect_sqlite_cache(filepath: str) -> Dict[str, Any]:
    """Inspect an SQLite database used as cache."""
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        result = {
            "type": "sqlite",
            "tables": tables,
            "table_info": {},
        }
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [(col[1], col[2]) for col in cursor.fetchall()]
            
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            sample_rows = cursor.fetchall()
            
            result["table_info"][table] = {
                "row_count": count,
                "columns": columns,
                "sample_rows": [str(row)[:200] for row in sample_rows],
            }
        
        conn.close()
        return result
    except Exception as e:
        return {"error": f"Failed to inspect SQLite: {str(e)}"}


def scan_directory_cache(
    dirpath: str,
    max_depth: int = 2,
    unpack_nested: bool = False,
    unpack_max_depth: int = 3,
) -> Dict[str, Any]:
    """Scan a directory for cache files and summarize contents."""
    path = Path(dirpath)
    if not path.exists() or not path.is_dir():
        return {"error": "Directory not found or not accessible"}

    result: Dict[str, Any] = {
        "path": str(path.absolute()),
        "total_files": 0,
        "total_dirs": 0,
        "total_size": 0,
        "file_types": {},
        "files": [],
        "cache_files": [],
    }

    cache_extensions = {".pkl", ".pickle", ".json", ".db", ".sqlite"}

    for root, dirs, files in os.walk(dirpath):
        current_depth = root.count(os.sep) - str(path).count(os.sep)
        if current_depth >= max_depth:
            dirs.clear()
            continue

        result["total_dirs"] += len(dirs)

        for filename in files:
            filepath = os.path.join(root, filename)
            result["total_files"] += 1

            try:
                size = os.path.getsize(filepath)
                result["total_size"] += size

                ext = Path(filename).suffix.lower() or "no_extension"
                result["file_types"][ext] = result["file_types"].get(ext, 0) + 1

                file_info = {
                    "name": filename,
                    "size": format_size(size),
                    "relative_path": os.path.relpath(filepath, dirpath),
                }
                result["files"].append(file_info)

                if unpack_nested and ext in cache_extensions:
                    cache_info = inspect_cache(filepath, unpack_nested=True, unpack_max_depth=unpack_max_depth)
                    cache_info["relative_path"] = file_info["relative_path"]
                    result["cache_files"].append(cache_info)

            except (OSError, PermissionError):
                continue

    result["total_size_human"] = format_size(result["total_size"])
    result["files"] = sorted(result["files"], key=lambda x: x["relative_path"])

    return result


def inspect_cache(
    path: str,
    cache_type: Optional[str] = None,
    unpack_nested: bool = False,
    unpack_max_depth: int = 3,
) -> Dict[str, Any]:
    """Main inspection function that routes to appropriate handler."""
    path_obj = Path(path)

    if not path_obj.exists():
        return {"error": f"Path does not exist: {path}"}

    if cache_type == "pickle" or path.endswith(".pkl") or path.endswith(".pickle"):
        return inspect_pickle_file(path, unpack_nested=unpack_nested, max_depth=unpack_max_depth)

    if cache_type == "json" or path.endswith(".json"):
        return inspect_json_file(path, unpack_nested=unpack_nested, max_depth=unpack_max_depth)

    if cache_type == "sqlite" or path.endswith(".db") or path.endswith(".sqlite"):
        return inspect_sqlite_cache(path)

    if path_obj.is_dir():
        return scan_directory_cache(
            path,
            unpack_nested=unpack_nested,
            unpack_max_depth=unpack_max_depth,
        )

    return get_file_info(path)


def find_common_cache_locations() -> List[str]:
    """Find common cache directories on the system."""
    locations = []
    home = Path.home()
    
    common_paths = [
        home / ".cache",
        home / ".local" / "share" / "cache",
        home / "Library" / "Caches",
        Path("/tmp"),
        Path("/var/cache"),
    ]
    
    for loc in common_paths:
        if loc.exists():
            locations.append(str(loc))
    
    return locations


def main():
    parser = argparse.ArgumentParser(
        description="Cache Inspector - Tool to inspect and debug cache contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.cache
  %(prog)s /tmp/my_cache.pkl --type pickle
  %(prog)s cache.db --type sqlite
  %(prog)s --find-locations
  %(prog)s data.pkl --unpack-nested --unpack-depth 5
        """
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="Path to cache file or directory to inspect"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["pickle", "json", "sqlite", "auto"],
        default="auto",
        help="Force specific cache type interpretation"
    )
    parser.add_argument(
        "--find-locations", "-f",
        action="store_true",
        help="List common cache locations on this system"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output with all details"
    )
    parser.add_argument(
        "--unpack-nested", "-u",
        action="store_true",
        help="Recursively unpack nested cache structures (e.g., pickles containing JSON)"
    )
    parser.add_argument(
        "--unpack-depth", "-d",
        type=int,
        default=3,
        help="Maximum depth for nested unpacking (default: 3)"
    )

    args = parser.parse_args()

    if args.find_locations:
        locations = find_common_cache_locations()
        if args.output == "json":
            print(json.dumps({"cache_locations": locations}, indent=2))
        else:
            print("Common cache locations on this system:")
            for loc in locations:
                print(f"  - {loc}")
        return 0

    if not args.path:
        parser.print_help()
        return 1

    result = inspect_cache(
        args.path,
        args.type if args.type != "auto" else None,
        unpack_nested=args.unpack_nested,
        unpack_max_depth=args.unpack_depth,
    )

    if args.output == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        print_cache_report(result, args.verbose)

    return 0 if "error" not in result else 1


def _print_nested_structure(data: Dict[str, Any], indent: int = 0) -> None:
    """Print nested structure with indentation."""
    prefix = "  " * indent
    item_type = data.get("type", "unknown")
    
    if "value" in data:
        print(f"{prefix}{item_type}: {data['value']}")
        return
    
    if "children" in data:
        children = data["children"]
        if isinstance(children, dict):
            for key, child in children.items():
                print(f"{prefix}{key} ({item_type}):")
                _print_nested_structure(child, indent + 1)
        elif isinstance(children, list):
            for i, child in enumerate(children):
                print(f"{prefix}[{i}] ({item_type}):")
                _print_nested_structure(child, indent + 1)


def print_cache_report(result: Dict[str, Any], verbose: bool = False) -> None:
    """Print a formatted text report of cache inspection results."""
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print("=" * 60)
    print("CACHE INSPECTION REPORT")
    print("=" * 60)

    if "path" in result:
        print(f"\nPath: {result['path']}")

    if "type" in result:
        print(f"Type: {result['type'].upper()}")

    if "data_type" in result:
        print(f"Data Type: {result['data_type']}")

    if "size_bytes" in result:
        print(f"\nSize: {result['size_human']} ({result['size_bytes']:,} bytes)")
        print(f"Created: {result['created']}")
        print(f"Modified: {result['modified']}")
        print(f"MD5: {result['md5']}")

    if "total_files" in result:
        print(f"\nDirectory Statistics:")
        print(f"  Total Files: {result['total_files']}")
        print(f"  Total Directories: {result['total_dirs']}")
        print(f"  Total Size: {result['total_size_human']}")

        if result["file_types"]:
            print(f"\n  File Types:")
            for ext, count in sorted(result["file_types"].items()):
                print(f"    {ext}: {count} files")

    if "item_count" in result:
        print(f"\nItem Count: {result['item_count']:,}")

    if "top_level_keys" in result and result["top_level_keys"]:
        print(f"\nTop-level Keys (first 20):")
        for key in result["top_level_keys"]:
            print(f"  - {key}")

    if "tables" in result:
        print(f"\nSQLite Tables: {', '.join(result['tables'])}")
        for table, info in result.get("table_info", {}).items():
            print(f"\n  Table: {table}")
            print(f"    Rows: {info['row_count']:,}")
            print(f"    Columns: {', '.join(f'{c[0]} ({c[1]})' for c in info['columns'])}")
            if verbose and info["sample_rows"]:
                print(f"    Sample Rows:")
                for row in info["sample_rows"]:
                    print(f"      {row}")

    if "nested_structure" in result and result["nested_structure"]:
        print(f"\nNested Structure:")
        _print_nested_structure(result["nested_structure"])

    if "sample_data" in result and result["sample_data"]:
        print(f"\nSample Data:")
        if isinstance(result["sample_data"], dict):
            for key, value in result["sample_data"].items():
                print(f"  {key}: {value}")
        elif isinstance(result["sample_data"], list):
            for i, item in enumerate(result["sample_data"]):
                print(f"  [{i}]: {item}")
        else:
            print(f"  {result['sample_data']}")

    if "files" in result and result["files"]:
        print(f"\nFiles (first 50):")
        for f in result["files"][:50]:
            print(f"  {f['relative_path']} ({f['size']})")
        if len(result["files"]) > 50:
            print(f"  ... and {len(result['files']) - 50} more files")

    if "cache_files" in result and result["cache_files"]:
        print(f"\nCache Files (with nested content):")
        for cf in result["cache_files"]:
            print(f"\n  File: {cf.get('relative_path', 'unknown')}")
            if "nested_structure" in cf:
                _print_nested_structure(cf["nested_structure"], indent=2)
            elif "item_count" in cf:
                print(f"    Items: {cf['item_count']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    sys.exit(main())
