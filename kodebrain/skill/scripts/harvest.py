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
  python3 harvest.py --build-index nodes.json        # build file-index.json from nodes
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
    'node_modules', 'dist', 'build', 'out',
    '__pycache__', 'venv', '.mypy_cache',
    'coverage', 'htmlcov',
    'vendor', 'target', '.gradle',
}

# Next.js App Router filenames — discovered by convention, never imported
NEXTJS_APP_ROUTER_NAMES = {
    'route', 'page', 'layout', 'loading', 'error',
    'not-found', 'template', 'default',
}

TEST_PATTERNS = re.compile(
    r'(\.test\.|\.spec\.|_test\.|_spec\.)|'
    r'(/|^)(test|tests|spec|__tests__)/',
    re.IGNORECASE,
)

# Entry point filenames — zero importers is expected, not a signal of being unused
ENTRY_POINT_NAMES = {'server', 'main', 'index', 'app', 'cli', 'cmd', 'run', 'start'}

# Framework config / declaration files — discovered by convention, not imported
CONFIG_FILE_NAMES = {
    'next.config', 'next-env.d',
    'playwright.config', 'jest.config', 'vitest.config',
    'tailwind.config', 'postcss.config', 'eslint.config',
    'vite.config', 'webpack.config',
    'tsconfig', 'jsconfig',
}

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
# Re-export: export { X } from '...' or export * from '...'
_TS_REEXPORT = re.compile(r'^export\s+(?:\{[^}]*\}|\*)\s+from\s+[\'"]([^\'"]+)[\'"]', re.MULTILINE)
# Dynamic import: import('...')
_TS_DYNAMIC_IMPORT = re.compile(r'\bimport\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', re.MULTILINE)

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
    imports = (
        _TS_IMPORT.findall(content)
        + _TS_REQUIRE.findall(content)
        + _TS_REEXPORT.findall(content)
        + _TS_DYNAMIC_IMPORT.findall(content)
    )
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


def _is_nextjs_app_router(path: str) -> bool:
    """Next.js App Router files under app/ — file-system routed, never imported."""
    p = Path(path)
    stem = p.stem.lower()
    if stem not in NEXTJS_APP_ROUTER_NAMES:
        return False
    # Must be inside an app/ directory somewhere in the path
    parts = p.parts
    return any(part == 'app' for part in parts[:-1])


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

    # Next.js App Router files — discovered by file-system convention, not imports
    if _is_nextjs_app_router(path):
        return 'active'

    # Framework config / declaration files — never imported by project code
    if Path(path).stem in CONFIG_FILE_NAMES:
        return 'active'

    # Standalone scripts in scripts/ — run directly, not imported
    if Path(path).parts[0] == 'scripts':
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
        for raw_imp in data.get('imports', []):
            # Resolve TypeScript path aliases: @/ → src/
            if raw_imp.startswith('@/'):
                imp = 'src/' + raw_imp[2:]
            else:
                # Normalize: strip leading ./ and leading slashes
                imp = raw_imp.lstrip('./')

            imp_no_ext = str(Path(imp).with_suffix('')) if Path(imp).suffix in SOURCE_EXTENSIONS else imp
            imp_stem = Path(imp).stem

            for candidate in paths:
                if candidate == importer:
                    continue
                cand_no_ext = str(Path(candidate).with_suffix(''))
                cand_stem = Path(candidate).stem
                if (
                    cand_no_ext == imp_no_ext
                    or cand_no_ext.endswith('/' + imp_no_ext)
                    or cand_stem == imp_stem
                    or candidate == imp
                    or candidate == imp + Path(candidate).suffix
                    # Barrel resolution: `@/lib/foo` → `src/lib/foo/index.ts`
                    or cand_no_ext == imp_no_ext + '/index'
                    or cand_no_ext.endswith('/' + imp_no_ext + '/index')
                ):
                    if importer not in reverse[candidate]:
                        reverse[candidate].append(importer)
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
        # Skip hidden directories (dot-prefix) and named ignore dirs
        # Check intermediate parts only (not the filename itself)
        rel_parts = p.relative_to(root).parts[:-1]
        if any(part.startswith('.') or part in IGNORE_DIRS for part in rel_parts):
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


# ── File-index builder ────────────────────────────────────────────────────────

def build_file_index(nodes_path: Path) -> dict[str, list[str]]:
    """
    Invert nodes.json source_files → file-index.json.

    For every node that lists source_files, adds node_id to the index entry
    for each file.  Files not referenced by any node get an empty list.
    """
    nodes = json.loads(nodes_path.read_text(encoding='utf-8'))
    index: dict[str, list[str]] = {}
    for node in nodes:
        node_id = node.get('id', '')
        for src in node.get('source_files', []):
            index.setdefault(src, [])
            if node_id and node_id not in index[src]:
                index[src].append(node_id)
    return index


# ── Benchmark ─────────────────────────────────────────────────────────────────

def run_benchmark(kb_project_dir: Path, source_root: Path | None = None) -> dict:
    """
    Compute all KB health metrics from graph files. Pure data — no LLM judgment.

    kb_project_dir: the docs/brain/projects/<name>/ directory (contains graph/ and reports/)
    source_root:    optional project source root, used for token efficiency numbers
    """
    graph_dir = kb_project_dir / 'graph'
    reports_dir = kb_project_dir / 'reports'

    # Load graph files
    nodes: list[dict] = json.loads((graph_dir / 'nodes.json').read_text())
    edges: list[dict] = json.loads((graph_dir / 'edges.json').read_text())
    file_index: dict[str, list[str]] = json.loads((graph_dir / 'file-index.json').read_text())
    file_hashes: dict[str, str] = json.loads((graph_dir / 'file-hashes.json').read_text())

    node_map = {n['id']: n for n in nodes}

    # ── Coverage ──────────────────────────────────────────────────────────────
    total_source_files = len(file_hashes)
    mapped_files = sum(1 for v in file_index.values() if v)
    unmapped_files = total_source_files - mapped_files
    coverage_pct = mapped_files / total_source_files * 100 if total_source_files else 0

    # ── Node counts ───────────────────────────────────────────────────────────
    from collections import Counter
    type_counts = Counter(n['type'] for n in nodes)
    status_counts = Counter(n['status'] for n in nodes)
    conf_counts = Counter(n['confidence'] for n in nodes)

    # ── Edge counts ───────────────────────────────────────────────────────────
    edge_type_counts = Counter(e['type'] for e in edges)

    def get_domain(node_id: str) -> str | None:
        n = node_map.get(node_id)
        return n.get('domain') if n else None

    cross_domain_edges = [
        e for e in edges
        if (d1 := get_domain(e['from'])) and (d2 := get_domain(e['to'])) and d1 != d2
    ]

    # ── Graph metrics ─────────────────────────────────────────────────────────
    degree: Counter = Counter()
    for e in edges:
        degree[e['from']] += 1
        degree[e['to']] += 1

    orphan_nodes = [n['id'] for n in nodes if degree[n['id']] == 0]
    avg_degree = (2 * len(edges) / len(nodes)) if nodes else 0
    top_hubs = [
        {'id': nid, 'degree': deg, 'type': node_map[nid]['type']}
        for nid, deg in degree.most_common(5)
        if nid in node_map
    ]

    # ── Risk surface ──────────────────────────────────────────────────────────
    risk_nodes = [n for n in nodes if n['type'] == 'caveat']
    legacy_nodes = [
        n for n in nodes
        if n['status'] in ('legacy', 'deprecated', 'partially_migrated', 'unused')
    ]

    # Severity breakdown from node 'severity' field
    severity_counts: Counter = Counter()
    for n in risk_nodes:
        severity_counts[n.get('severity', 'untagged')] += 1

    def _count_headings(md_path: Path) -> int:
        if not md_path.exists():
            return 0
        import re
        return len(re.findall(r'^## ', md_path.read_text(), re.MULTILINE))

    needs_review_items = _count_headings(reports_dir / 'needs-review.md')
    suspected_legacy_items = _count_headings(reports_dir / 'suspected-legacy.md')

    # ── Quality scores ────────────────────────────────────────────────────────
    n_total = len(nodes)
    confidence_score = (
        conf_counts.get('verified', 0) * 100
        + conf_counts.get('source_supported', 0) * 80
        + conf_counts.get('inferred', 0) * 40
        + conf_counts.get('ambiguous', 0) * 10
    ) / n_total if n_total else 0

    coverage_score = coverage_pct
    connectedness_score = 100 - (len(orphan_nodes) / n_total * 100) if n_total else 0
    risk_score = min(100, len(risk_nodes) * 20 + len(legacy_nodes) * 10)
    overall_score = (coverage_score + confidence_score + connectedness_score + risk_score) / 4

    def _grade(score: float) -> str:
        if score >= 90: return 'Excellent'
        if score >= 75: return 'Good'
        if score >= 60: return 'Fair'
        return 'Needs work'

    # ── Token efficiency ──────────────────────────────────────────────────────
    kb_md_bytes = sum(p.stat().st_size for p in kb_project_dir.rglob('*.md'))
    kb_json_bytes = sum(p.stat().st_size for p in graph_dir.glob('*.json'))
    kb_total_bytes = kb_md_bytes + kb_json_bytes

    source_bytes: int | None = None
    if source_root:
        source_bytes = sum(
            (source_root / rel).stat().st_size
            for rel in file_hashes
            if (source_root / rel).exists()
        )

    # ── Assemble result ───────────────────────────────────────────────────────
    result = {
        'coverage': {
            'total_source_files': total_source_files,
            'mapped_files': mapped_files,
            'unmapped_files': unmapped_files,
            'coverage_pct': round(coverage_pct, 1),
        },
        'nodes': {
            'total': n_total,
            'by_type': dict(type_counts),
            'by_status': dict(status_counts),
            'by_confidence': dict(conf_counts),
        },
        'edges': {
            'total': len(edges),
            'by_type': dict(edge_type_counts),
            'cross_domain': len(cross_domain_edges),
        },
        'graph': {
            'avg_degree': round(avg_degree, 1),
            'orphan_count': len(orphan_nodes),
            'orphan_nodes': orphan_nodes,
            'top_hubs': top_hubs,
        },
        'risk_surface': {
            'risk_nodes': len(risk_nodes),
            'risk_nodes_by_severity': dict(severity_counts),
            'legacy_deprecated_nodes': len(legacy_nodes),
            'needs_review_items': needs_review_items,
            'suspected_legacy_items': suspected_legacy_items,
        },
        'scores': {
            'coverage': round(coverage_score),
            'confidence': round(confidence_score),
            'connectedness': round(connectedness_score),
            'risk_awareness': round(risk_score),
            'overall': round(overall_score),
            'grade': _grade(overall_score),
        },
        'token_efficiency': {
            'kb_md_bytes': kb_md_bytes,
            'kb_json_bytes': kb_json_bytes,
            'kb_total_bytes': kb_total_bytes,
            'kb_est_tokens': kb_total_bytes // 4,
            'source_bytes': source_bytes,
            'source_est_tokens': (source_bytes // 4) if source_bytes else None,
            'compression_ratio': round(source_bytes / kb_total_bytes, 1) if source_bytes else None,
        },
    }
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description='kodebrain harvest — deterministic source extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--build-index',
        metavar='NODES_JSON',
        help='Build file-index.json by inverting source_files in nodes.json. '
             'Writes to <nodes_dir>/file-index.json. All other args ignored.',
    )
    parser.add_argument(
        '--benchmark',
        metavar='KB_PROJECT_DIR',
        help='Compute KB health metrics from graph files. '
             'Pass the docs/brain/projects/<name>/ directory. '
             'Use --source-root to include token efficiency numbers.',
    )
    parser.add_argument(
        '--source-root',
        metavar='DIR',
        help='Project source root for token efficiency metrics (used with --benchmark).',
    )
    parser.add_argument('root', nargs='?', help='Project root directory')
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

    # ── --benchmark mode ──────────────────────────────────────────────────────
    if args.benchmark:
        kb_dir = Path(args.benchmark).resolve()
        if not kb_dir.exists():
            print(f'Error: KB project dir "{kb_dir}" does not exist', file=sys.stderr)
            sys.exit(1)
        source_root = Path(args.source_root).resolve() if args.source_root else None
        metrics = run_benchmark(kb_dir, source_root)
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        return

    # ── --build-index mode ────────────────────────────────────────────────────
    if args.build_index:
        nodes_path = Path(args.build_index).resolve()
        if not nodes_path.exists():
            print(f'Error: nodes file "{nodes_path}" does not exist', file=sys.stderr)
            sys.exit(1)
        index = build_file_index(nodes_path)
        out_path = nodes_path.parent / 'file-index.json'
        out_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
        print(
            f'file-index.json written: {len(index)} files, '
            f'{sum(len(v) for v in index.values())} node references → {out_path}',
            file=sys.stderr,
        )
        return

    if not args.root:
        parser.error('root is required unless --build-index or --benchmark is used')

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
