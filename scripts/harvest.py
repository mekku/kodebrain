#!/usr/bin/env python3
"""
kodebrain harvest — deterministic source extraction for any project.

Replaces the H1–H5 grep/hash shell commands from the Harvest Phase.
Outputs structured JSON briefs that Claude reads instead of raw source files.

Usage:
  python3 harvest.py <root>                          # full harvest (init)
  python3 harvest.py <root> --hashes file-hashes.json  # incremental (scan/update)
  python3 harvest.py <root> --files src/a.ts src/b.ts  # targeted (update --files)
  python3 harvest.py <root> --output briefs.json     # write to file instead of stdout
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# ── File classification ────────────────────────────────────────────────────────

SOURCE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx',   # TypeScript / JavaScript
    '.py',                           # Python
    '.go',                           # Go
    '.rs',                           # Rust
    '.java',                         # Java
    '.rb',                           # Ruby
    '.php',                          # PHP
    '.cs',                           # C#
    '.swift',                        # Swift
    '.kt',                           # Kotlin
}

IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', 'out', '.next',
    '__pycache__', '.venv', 'venv', '.mypy_cache',
    'coverage', '.coverage', 'htmlcov',
    'vendor', 'target', '.gradle',
}

TEST_PATTERNS = re.compile(
    r'(\.test\.|\.spec\.|_test\.|_spec\.)|'
    r'(/|^)(test|tests|spec|__tests__)/',
    re.IGNORECASE,
)

# Entry point filenames — zero importers is expected, not a signal of being unused
ENTRY_POINT_NAMES = {'server', 'main', 'index', 'app', 'cli', 'cmd', 'run', 'start'}

# ── Language-specific extraction ───────────────────────────────────────────────

# TypeScript / JavaScript
_TS_EXPORT = re.compile(
    r'^export\s+(?:default\s+)?'
    r'(async\s+function|function|class|const|let|type|interface|enum)\s+'
    r'(\w+)',
    re.MULTILINE,
)
_TS_EXPORT_DEFAULT = re.compile(r'^export\s+default\s+(\w+)', re.MULTILINE)
_TS_ROUTE = re.compile(
    r'\b(app|router|[A-Za-z]+[Rr]outer)\.'
    r'(get|post|put|delete|patch|use)\s*\(',
    re.MULTILINE,
)
_TS_IMPORT = re.compile(
    r'^import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*]+(?:\s+as\s+\w+)?)\s+from\s+'
    r'[\'"]([^\'"]+)[\'"]',
    re.MULTILINE,
)
_TS_REQUIRE = re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', re.MULTILINE)

# Python
_PY_DEF = re.compile(r'^(def|class|async def)\s+([A-Za-z_]\w*)', re.MULTILINE)
_PY_ROUTE = re.compile(
    r'@\s*(\w+(?:\.\w+)?)\s*\.\s*(get|post|put|delete|patch|route)',
    re.MULTILINE,
)
_PY_IMPORT = re.compile(
    r'^(?:from\s+(\S+)\s+import\s+\S|import\s+(\S+))',
    re.MULTILINE,
)

# Go
_GO_EXPORT = re.compile(r'^func\s+([A-Z]\w*)', re.MULTILINE)
_GO_METHOD = re.compile(r'^func\s+\(\w+\s+\*?\w+\)\s+([A-Z]\w*)', re.MULTILINE)
_GO_IMPORT = re.compile(r'^\s+"([^"]+)"', re.MULTILINE)

# Status signals (all languages)
_DEPRECATED = re.compile(
    r'@deprecated|'
    r'//\s*DEPRECATED|//\s*deprecated|'
    r'#\s*DEPRECATED|#\s*deprecated|'
    r'/\*\*?\s*@deprecated',
    re.IGNORECASE,
)
_TODO_MIGRATE = re.compile(
    r'TODO[:\s].{0,60}(remov|migrat|deprecat|replac)',
    re.IGNORECASE,
)
_FIXME = re.compile(r'FIXME[:\s]', re.IGNORECASE)

# Legacy name patterns (applied to file stem only)
_LEGACY_STEM = re.compile(
    r'(?i)(^|[._-])(v1|v2old|old|legacy|backup|deprecated|obsolete)([._-]|$)'
)


def _extract_ts(content: str) -> dict:
    exports = [m.group(2) for m in _TS_EXPORT.finditer(content)]
    exports += _TS_EXPORT_DEFAULT.findall(content)
    routes = [f"{m.group(1)}.{m.group(2)}()" for m in _TS_ROUTE.finditer(content)]
    imports = _TS_IMPORT.findall(content) + _TS_REQUIRE.findall(content)
    return {'exports': exports, 'routes': routes, 'imports': imports}


def _extract_py(content: str) -> dict:
    exports = [m.group(2) for m in _PY_DEF.finditer(content)]
    routes = [f"@{m.group(1)}.{m.group(2)}" for m in _PY_ROUTE.finditer(content)]
    imports = [m.group(1) or m.group(2) for m in _PY_IMPORT.finditer(content)]
    return {'exports': exports, 'routes': routes, 'imports': imports}


def _extract_go(content: str) -> dict:
    exports = _GO_EXPORT.findall(content) + _GO_METHOD.findall(content)
    imports = _GO_IMPORT.findall(content)
    return {'exports': exports, 'routes': [], 'imports': imports}


def _extract(path: Path, content: str) -> dict:
    ext = path.suffix.lower()
    if ext in {'.ts', '.tsx', '.js', '.jsx'}:
        return _extract_ts(content)
    if ext == '.py':
        return _extract_py(content)
    if ext == '.go':
        return _extract_go(content)
    return {'exports': [], 'routes': [], 'imports': []}


def _signals(content: str) -> list[dict]:
    found = []
    for pattern in (_DEPRECATED, _TODO_MIGRATE, _FIXME):
        for m in pattern.finditer(content):
            line_no = content[: m.start()].count('\n') + 1
            found.append({'line': line_no, 'text': m.group(0).strip()[:100]})
    # Deduplicate by line number
    seen = set()
    deduped = []
    for s in sorted(found, key=lambda x: x['line']):
        if s['line'] not in seen:
            seen.add(s['line'])
            deduped.append(s)
    return deduped


def _is_test_file(path: str) -> bool:
    return bool(TEST_PATTERNS.search(path))


def _is_entry_point(path: str) -> bool:
    stem = Path(path).stem.lower()
    # Root-level or cmd/ entry points — zero importers expected
    parts = Path(path).parts
    return stem in ENTRY_POINT_NAMES and len(parts) <= 2


def _classify_status(
    path: str,
    exports: list,
    routes: list,
    signals: list,
    imported_by: list,
) -> str:
    stem = Path(path).stem

    # Test files are never "unused" — they're not imported by design
    if _is_test_file(path):
        return 'active'

    # Entry points are never "unused" — they're process roots, not imported
    if _is_entry_point(path) and not imported_by:
        return 'active'

    # Deprecated signal wins
    for s in signals:
        if _DEPRECATED.search(s['text']):
            return 'deprecated'

    # TODO: remove/migrate → partially_migrated
    for s in signals:
        if _TODO_MIGRATE.search(s['text']):
            return 'partially_migrated'

    # Legacy name pattern → suspected_legacy
    if _LEGACY_STEM.search(stem):
        return 'suspected_legacy'

    # Zero importers AND zero routes → suspected_unused
    if not imported_by and not routes:
        return 'suspected_unused'

    return 'active'


# ── Reverse import map ─────────────────────────────────────────────────────────

def _build_reverse_map(
    partial: dict[str, dict],
    root: Path,
) -> dict[str, list[str]]:
    """
    For each file, find which other files import it.
    Resolves relative imports like '../services/AuthService' to actual paths.
    """
    reverse: dict[str, list[str]] = {p: [] for p in partial}
    paths = list(partial.keys())

    # Build quick lookup: stem → [full_rel_path]
    stem_map: dict[str, list[str]] = {}
    for p in paths:
        stem = Path(p).stem
        stem_map.setdefault(stem, []).append(p)

    for importer, data in partial.items():
        importer_dir = str(Path(importer).parent)
        for raw_imp in data.get('imports', []):
            # Normalize: strip leading ./ and leading slashes
            imp = raw_imp.lstrip('./')
            # Try to match by: file stem, or path suffix
            matched = False
            for candidate in paths:
                if candidate == importer:
                    continue
                cand_no_ext = str(Path(candidate).with_suffix(''))
                cand_stem = Path(candidate).stem
                if (
                    cand_no_ext.endswith(imp)
                    or cand_stem == imp
                    or cand_stem == Path(imp).stem
                    or candidate == imp
                    or candidate == imp + Path(candidate).suffix
                ):
                    if importer not in reverse[candidate]:
                        reverse[candidate].append(importer)
                    matched = True
                    break
    return reverse


# ── SHA-256 hashing ────────────────────────────────────────────────────────────

def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── File discovery ─────────────────────────────────────────────────────────────

def _find_source_files(root: Path) -> list[Path]:
    results = []
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        if p.suffix not in SOURCE_EXTENSIONS:
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        results.append(p)
    return results


# ── Main harvest ───────────────────────────────────────────────────────────────

def harvest(
    root: Path,
    existing_hashes: dict | None = None,
    target_files: list[Path] | None = None,
) -> dict:
    """
    Run the full harvest pipeline.

    Args:
        root:            Project root directory.
        existing_hashes: Contents of file-hashes.json (if any). Used for dirty detection.
        target_files:    If given, harvest only these files (for --files mode).

    Returns:
        {
          "root": str,
          "hashes": { rel_path: sha256 },
          "dirty": [ rel_path, ... ],   # files processed this run
          "files": {
            rel_path: {
              "path": str,
              "exports": [...],
              "routes": [...],
              "imports": [...],
              "imported_by": [...],
              "status_signals": [{line, text}, ...],
              "status": str,
              "has_test": bool,
            }
          }
        }
    """
    source_files = target_files if target_files else _find_source_files(root)

    # Phase H1 — hash + extract raw data
    partial: dict[str, dict] = {}
    hashes: dict[str, str] = {}
    dirty: list[str] = []

    for path in source_files:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)

        file_hash = _hash_file(path)
        hashes[rel] = file_hash

        if existing_hashes is not None and existing_hashes.get(rel) == file_hash:
            continue  # unchanged — skip

        dirty.append(rel)
        try:
            content = path.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            print(f'Warning: cannot read {rel}: {e}', file=sys.stderr)
            continue

        extracted = _extract(path, content)
        sigs = _signals(content)
        partial[rel] = {**extracted, 'signals': sigs}

    # Phase H4 (reverse) — build import map from dirty files
    reverse = _build_reverse_map(partial, root)

    # Phase H5 + H6 — classify status, finalize briefs
    files: dict[str, dict] = {}
    for rel, data in partial.items():
        importers = reverse.get(rel, [])
        status = _classify_status(
            rel,
            data['exports'],
            data['routes'],
            data['signals'],
            importers,
        )
        # Check for a sibling test file
        p = root / rel
        stem_no_ext = str(p.with_suffix(''))
        has_test = any(
            (root / (stem_no_ext + suffix)).exists()
            for suffix in ('.test.ts', '.spec.ts', '.test.js', '.spec.js',
                           '_test.go', '_test.py', '.test.tsx', '.spec.tsx')
        )
        files[rel] = {
            'path': rel,
            'exports': data['exports'],
            'routes': data['routes'],
            'imports': data['imports'],
            'imported_by': importers,
            'status_signals': data['signals'],
            'status': status,
            'has_test': has_test,
            'is_test': _is_test_file(rel),
        }

    # On first run (no existing_hashes), mark all files as dirty
    if existing_hashes is None:
        dirty = list(files.keys())

    return {
        'root': str(root),
        'hashes': hashes,
        'dirty': dirty,
        'files': files,
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='kodebrain harvest — deterministic source extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('root', help='Project root directory')
    parser.add_argument(
        '--hashes',
        metavar='FILE',
        help='Path to existing file-hashes.json for incremental harvest',
    )
    parser.add_argument(
        '--files',
        nargs='+',
        metavar='FILE',
        help='Harvest only these specific files (absolute or relative to root)',
    )
    parser.add_argument(
        '--output',
        metavar='FILE',
        help='Write JSON output to this file (default: stdout)',
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f'Error: root "{root}" does not exist', file=sys.stderr)
        sys.exit(1)

    # Load existing hashes for dirty detection
    existing_hashes: dict | None = None
    if args.hashes:
        hashes_path = Path(args.hashes)
        if hashes_path.exists():
            try:
                existing_hashes = json.loads(hashes_path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f'Warning: cannot load hashes from {args.hashes}: {e}', file=sys.stderr)

    # Resolve target files if given
    target_files: list[Path] | None = None
    if args.files:
        target_files = []
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                p = root / p
            if p.exists():
                target_files.append(p)
            else:
                print(f'Warning: file not found: {f}', file=sys.stderr)

    result = harvest(root, existing_hashes, target_files)

    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output_json, encoding='utf-8')
        print(
            f'Harvest complete: {len(result["files"])} files processed '
            f'({len(result["dirty"])} dirty) → {args.output}',
            file=sys.stderr,
        )
    else:
        print(output_json)


if __name__ == '__main__':
    main()
