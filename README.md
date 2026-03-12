# cache-inspector

A CLI tool to inspect and debug cache contents. Because sometimes you just need to peek inside that mysterious `.cache` folder and figure out what's eating up all your disk space.

## Why I Built This

I kept running into situations where:
- My cache directory was 5GB and I had no idea why
- I found a `.pkl` file and couldn't remember what was in it
- Some app was caching stuff to SQLite and I needed to debug it
- I just wanted to know what format a cache file was without writing a quick Python script every time

So here we are.

## Installation

```bash
pip install -r requirements.txt
```

Or just run it directly if you're lazy:

```bash
python cache_inspector.py --help
```

## Usage

### Inspect a directory

```bash
python cache_inspector.py ~/.cache
```

This gives you a breakdown of files, sizes, and types. Good for finding cache hogs.

### Inspect a pickle file

```bash
python cache_inspector.py model_cache.pkl
python cache_inspector.py data.pkl --type pickle
```

Shows you the keys, item count, and a sample of what's inside. No need to unpickle it manually.

### Inspect a JSON cache

```bash
python cache_inspector.py api_responses.json
```

Same deal - shows structure and sample data.

### Inspect an SQLite cache

```bash
python cache_inspector.py app_cache.db
python cache_inspector.py cache.sqlite --type sqlite
```

Lists tables, row counts, columns, and sample rows.

### Unpack nested cache structures

```bash
python cache_inspector.py nested_data.pkl --unpack-nested
python cache_inspector.py complex_cache.json -u --unpack-depth 5
```

Recursively unpacks nested structures like pickles containing JSON, dicts with lists of dicts, etc. Shows the full hierarchy up to the specified depth.

### Find cache locations

```bash
python cache_inspector.py --find-locations
```

Shows common cache directories on your system. Handy when you're not sure where to look.

### JSON output

```bash
python cache_inspector.py ~/.cache --output json
```

Pipe it to `jq` or parse it in another script.

## Output Format

The text output is formatted as a report. Here's what you get:

```
============================================================
CACHE INSPECTION REPORT
============================================================

Path: /home/user/.cache
Type: DIRECTORY

Directory Statistics:
  Total Files: 1247
  Total Directories: 34
  Total Size: 2.34 GB

  File Types:
    .json: 45 files
    .pkl: 12 files
    .db: 3 files
    ...

Files (first 50):
  pip/http/abc123 (1.23 KB)
  ...

============================================================
```

## What It Handles

- **Directories**: Scans and summarizes contents
- **Pickle files**: `.pkl`, `.pickle` - shows structure without loading everything
- **JSON files**: `.json` - parses and displays keys/samples
- **SQLite databases**: `.db`, `.sqlite` - lists tables and schemas
- **Generic files**: Shows size, timestamps, MD5 hash

## Limitations

- Large pickle files might take a moment to load
- SQLite inspection is read-only (by design)
- No support for Redis, Memcached, or other network caches
- Nested unpacking is limited to depth 3 by default (configurable via `--unpack-depth`)

## Adding More Formats

The code is structured so adding new cache types is straightforward. Just add a new `inspect_*` function and wire it up in `inspect_cache()`. Pull requests welcome.

## License

Do whatever you want with it.
