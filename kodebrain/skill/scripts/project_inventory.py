#!/usr/bin/env python3
"""
kodebrain project-inventory — architecture-aware project scanner.

Scans a project root for technology and infrastructure signals beyond
source-file exports/imports. Produces structured inventory for the
technology/runtime/architecture skeleton.

Detection categories:
  - language / runtime manifests
  - package managers
  - frontend / backend frameworks
  - DB clients / ORMs
  - cache clients
  - queues / event systems
  - infrastructure / deployment files
  - Docker / container files
  - CI configuration
  - environment / config conventions
  - API styles
  - worker / scheduler entry points

Usage:
  python3 project_inventory.py <root>              # full inventory
  python3 project_inventory.py <root> --output f.json  # write to file
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ── Manifest file names known to each ecosystem ───────────────────────────────

_MANIFESTS: dict[str, list[str]] = {
    "node": ["package.json"],
    "python": ["pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt"],
    "go": ["go.mod", "go.sum"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
    "swift": ["Package.swift"],
    "dotnet": ["*.csproj", "*.sln"],
    "kotlin": ["build.gradle.kts", "settings.gradle.kts"],
}

# ── Framework / library fingerprint: (filename, content_pattern) ──────────────

_FINGERPRINTS: list[tuple[str, str, str, str]] = [  # (file, pattern, category, name)
    # Frontend
    ("package.json", "next", "frontend", "Next.js"),
    ("next.config.*", "", "frontend", "Next.js"),
    ("package.json", "react", "frontend", "React"),
    ("package.json", "vue", "frontend", "Vue"),
    ("package.json", "svelte", "frontend", "Svelte"),
    ("package.json", "angular", "frontend", "Angular"),
    ("package.json", "solid-js", "frontend", "SolidJS"),
    ("package.json", "remix", "frontend", "Remix"),
    ("package.json", "astro", "frontend", "Astro"),
    # CSS / UI
    ("tailwind.config.*", "", "frontend", "Tailwind CSS"),
    ("package.json", "tailwindcss", "frontend", "Tailwind CSS"),
    ("package.json", "shadcn", "frontend", "shadcn/ui"),
    ("package.json", "mui", "frontend", "Material UI"),
    ("package.json", "chakra", "frontend", "Chakra UI"),
    # Backend frameworks
    ("package.json", "express", "backend", "Express"),
    ("package.json", "fastify", "backend", "Fastify"),
    ("package.json", "hono", "backend", "Hono"),
    ("package.json", "elysia", "backend", "Elysia"),
    ("package.json", "koa", "backend", "Koa"),
    ("package.json", "nest", "backend", "NestJS"),
    ("pyproject.toml", "fastapi", "backend", "FastAPI"),
    ("pyproject.toml", "flask", "backend", "Flask"),
    ("pyproject.toml", "django", "backend", "Django"),
    ("pyproject.toml", "litestar", "backend", "Litestar"),
    ("go.mod", "gin-gonic", "backend", "Gin"),
    ("go.mod", "echo", "backend", "Echo"),
    ("go.mod", "fiber", "backend", "Fiber"),
    ("go.mod", "chi", "backend", "Chi"),
    ("Cargo.toml", "actix-web", "backend", "Actix Web"),
    ("Cargo.toml", "axum", "backend", "Axum"),
    ("Cargo.toml", "rocket", "backend", "Rocket"),
    # Database
    ("package.json", "prisma", "database", "Prisma"),
    ("package.json", "drizzle", "database", "Drizzle ORM"),
    ("package.json", "knex", "database", "Knex"),
    ("package.json", "typeorm", "database", "TypeORM"),
    ("package.json", "sequelize", "database", "Sequelize"),
    ("package.json", "mongoose", "database", "Mongoose"),
    ("package.json", "mysql2", "database", "MySQL"),
    ("package.json", "pg", "database", "PostgreSQL"),
    ("package.json", "postgres", "database", "PostgreSQL"),
    ("package.json", "better-sqlite3", "database", "SQLite"),
    ("package.json", "sqlite3", "database", "SQLite"),
    ("package.json", "mongodb", "database", "MongoDB"),
    ("prisma/schema.prisma", "", "database", "Prisma"),
    ("pyproject.toml", "sqlalchemy", "database", "SQLAlchemy"),
    ("pyproject.toml", "sqlmodel", "database", "SQLModel"),
    ("pyproject.toml", "psycopg", "database", "PostgreSQL"),
    ("pyproject.toml", "aiosqlite", "database", "SQLite"),
    ("go.mod", "pgx", "database", "PostgreSQL"),
    ("go.mod", "sqlx", "database", "SQLX"),
    ("go.mod", "gorm", "database", "GORM"),
    # Cache
    ("package.json", "redis", "cache", "Redis"),
    ("package.json", "ioredis", "cache", "Redis"),
    ("package.json", "lru-cache", "cache", "LRU Cache"),
    ("pyproject.toml", "redis", "cache", "Redis"),
    ("pyproject.toml", "aiocache", "cache", "AioCache"),
    ("go.mod", "go-redis", "cache", "Redis"),
    # Queue / Events
    ("package.json", "bull", "queue", "BullMQ"),
    ("package.json", "bullmq", "queue", "BullMQ"),
    ("package.json", "bee-queue", "queue", "Bee Queue"),
    ("package.json", "amqplib", "queue", "RabbitMQ"),
    ("package.json", "kafkajs", "queue", "Kafka"),
    ("package.json", "sqs", "queue", "AWS SQS"),
    ("package.json", "pulsar", "queue", "Pulsar"),
    ("package.json", "nats", "queue", "NATS"),
    ("pyproject.toml", "celery", "queue", "Celery"),
    ("pyproject.toml", "arq", "queue", "ARQ"),
    ("pyproject.toml", "dramatiq", "queue", "Dramatiq"),
    ("go.mod", "asynq", "queue", "Asynq"),
    ("go.mod", "machinery", "queue", "Machinery"),
    # Testing
    ("package.json", "vitest", "testing", "Vitest"),
    ("package.json", "jest", "testing", "Jest"),
    ("package.json", "mocha", "testing", "Mocha"),
    ("package.json", "playwright", "testing", "Playwright"),
    ("package.json", "cypress", "testing", "Cypress"),
    ("pyproject.toml", "pytest", "testing", "Pytest"),
    ("pyproject.toml", "unittest", "testing", "Unittest"),
    ("go.mod", "testify", "testing", "Testify"),
    # Build / Tooling
    ("package.json", "typescript", "build", "TypeScript"),
    ("package.json", "esbuild", "build", "esbuild"),
    ("package.json", "vite", "build", "Vite"),
    ("package.json", "webpack", "build", "Webpack"),
    ("package.json", "rollup", "build", "Rollup"),
    ("package.json", "tsup", "build", "tsup"),
    ("package.json", "turbo", "build", "Turborepo"),
    ("package.json", "nx", "build", "Nx"),
    ("pyproject.toml", "ruff", "build", "Ruff"),
    ("pyproject.toml", "mypy", "build", "Mypy"),
    ("pyproject.toml", "black", "build", "Black"),
    ("go.mod", "cobra", "build", "Cobra CLI"),
    # Validation
    ("package.json", "zod", "validation", "Zod"),
    ("package.json", "yup", "validation", "Yup"),
    ("package.json", "valibot", "validation", "Valibot"),
    ("package.json", "joi", "validation", "Joi"),
    ("pyproject.toml", "pydantic", "validation", "Pydantic"),
    # Auth
    ("package.json", "lucia", "auth", "Lucia Auth"),
    ("package.json", "next-auth", "auth", "NextAuth.js"),
    ("package.json", "clerk", "auth", "Clerk"),
    ("package.json", "auth0", "auth", "Auth0"),
    ("package.json", "passport", "auth", "Passport"),
    ("pyproject.toml", "python-jose", "auth", "JOSE"),
    ("pyproject.toml", "fastapi-users", "auth", "FastAPI Users"),
]

# ── Infrastructure file patterns ─────────────────────────────────────────────

_INFRA_PATTERNS: list[tuple[str, str]] = [  # (glob_pattern, description)
    ("Dockerfile*", "Docker"),
    ("docker-compose*.yml", "Docker Compose"),
    ("docker-compose*.yaml", "Docker Compose"),
    (".dockerignore", "Docker"),
    (".github/workflows/*.yml", "GitHub Actions"),
    (".github/workflows/*.yaml", "GitHub Actions"),
    (".gitlab-ci.yml", "GitLab CI"),
    ("Jenkinsfile", "Jenkins"),
    ("Makefile", "Make"),
    ("*.tf", "Terraform"),
    ("*.tfvars", "Terraform"),
    ("kubernetes/**/*.yml", "Kubernetes"),
    ("kubernetes/**/*.yaml", "Kubernetes"),
    ("k8s/**/*.yml", "Kubernetes"),
    ("helm/**/*", "Helm"),
    (".env.example", "Environment config"),
    (".env.template", "Environment config"),
    (".env.sample", "Environment config"),
    ("Procfile", "Heroku/Procfile"),
    ("fly.toml", "Fly.io"),
    ("render.yaml", "Render"),
    ("vercel.json", "Vercel"),
    ("netlify.toml", "Netlify"),
    ("serverless.yml", "Serverless Framework"),
    ("supabase/**/*", "Supabase"),
    ("firebase.json", "Firebase"),
    ("app.json", "Platform config"),
    ("nginx*.conf", "Nginx"),
    ("Caddyfile", "Caddy"),
]

# ── API style signals ────────────────────────────────────────────────────────

_API_SIGNALS: list[tuple[str, str, str]] = [  # (file, content_regex, style)
    ("package.json", "graphql", "GraphQL"),
    ("package.json", "apollo", "GraphQL (Apollo)"),
    ("package.json", "trpc", "tRPC"),
    ("package.json", "openapi", "REST (OpenAPI)"),
    ("package.json", "swagger", "REST (Swagger)"),
    ("pyproject.toml", "graphql", "GraphQL"),
    ("pyproject.toml", "grpcio", "gRPC"),
    ("go.mod", "graphql", "GraphQL"),
    ("go.mod", "grpc", "gRPC"),
    ("go.mod", "connectrpc", "Connect RPC"),
    ("*.proto", "", "gRPC / Protobuf"),
    ("*.graphql", "", "GraphQL schema"),
    ("schema.graphql", "", "GraphQL schema"),
]

# ── Worker / scheduler entry point signals ────────────────────────────────────

_WORKER_SIGNALS: list[tuple[str, str]] = [
    ("src/worker", "Worker entry point"),
    ("src/workers", "Worker entry points"),
    ("src/queue", "Queue consumer"),
    ("src/jobs", "Job definitions"),
    ("workers/", "Worker entry point"),
    ("jobs/", "Job definitions"),
    ("cmd/worker", "Worker CLI"),
    ("cmd/scheduler", "Scheduler CLI"),
    ("scripts/cron", "Cron script"),
    ("tasks/", "Background tasks"),
    ("celery", "Celery tasks"),
    ("consumer", "Event consumer"),
    ("subscriber", "Event subscriber"),
]

# ── Source file counting by extension ─────────────────────────────────────────

_SOURCE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".go", ".rs", ".java", ".rb", ".php",
    ".cs", ".swift", ".kt", ".scala", ".dart",
    ".css", ".scss", ".less",
    ".html", ".vue", ".svelte",
    ".sql",
    ".graphql", ".gql",
    ".proto",
    ".yaml", ".yml", ".toml", ".json",
}


# ── Main ──────────────────────────────────────────────────────────────────────

def _scan_manifests(root: Path) -> dict[str, Any]:
    """Find language and build manifests."""
    found: dict[str, list[str]] = {}
    for eco, names in _MANIFESTS.items():
        for name in names:
            if "*" in name:
                for p in sorted(root.glob(name)):
                    found.setdefault(eco, []).append(str(p.relative_to(root)))
            else:
                p = root / name
                if p.exists():
                    found.setdefault(eco, []).append(str(p.relative_to(root)))
    return found


def _scan_fingerprints(root: Path) -> dict[str, list[dict[str, str]]]:
    """Detect frameworks and libraries from manifest content patterns."""
    categorized: dict[str, list[dict[str, str]]] = {}
    seen: set[tuple[str, str]] = set()

    for file_pat, content_pat, category, name in _FINGERPRINTS:
        if "*" in file_pat:
            matches = list(root.glob(file_pat))
        else:
            p = root / file_pat
            matches = [p] if p.exists() else []

        for match in matches:
            if not content_pat:
                # File existence is enough signal
                if (category, name) not in seen:
                    categorized.setdefault(category, []).append(
                        {"name": name, "evidence": str(match.relative_to(root))}
                    )
                    seen.add((category, name))
                continue

            try:
                content = match.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue

            if content_pat.lower() in content:
                if (category, name) not in seen:
                    categorized.setdefault(category, []).append(
                        {"name": name, "evidence": str(match.relative_to(root))}
                    )
                    seen.add((category, name))

    return categorized


def _scan_infrastructure(root: Path) -> list[dict[str, str]]:
    """Find infrastructure and deployment files."""
    found: list[dict[str, str]] = []
    for pattern, desc in _INFRA_PATTERNS:
        for p in sorted(root.glob(pattern)):
            found.append({
                "file": str(p.relative_to(root)),
                "type": desc,
            })
    return found


def _scan_api_styles(root: Path) -> list[dict[str, str]]:
    """Detect API styles from manifests and schema files."""
    found: list[dict[str, str]] = []
    for file_pat, content_regex, style in _API_SIGNALS:
        if "*" in file_pat:
            matches = list(root.glob(file_pat))
        else:
            p = root / file_pat
            matches = [p] if p.exists() else []

        for match in matches:
            if not content_regex:
                found.append({
                    "style": style,
                    "evidence": str(match.relative_to(root)),
                })
                continue
            try:
                content = match.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if content_regex.lower() in content:
                found.append({
                    "style": style,
                    "evidence": str(match.relative_to(root)),
                })

    # Deduplicate by style
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for f in found:
        if f["style"] not in seen:
            seen.add(f["style"])
            deduped.append(f)
    return deduped


def _scan_entry_points(root: Path) -> dict[str, list[str]]:
    """Detect runtime entry points: servers, workers, schedulers, CLIs."""
    entries: dict[str, list[str]] = {
        "servers": [],
        "workers": [],
        "schedulers": [],
        "cli": [],
    }

    # Server entry points
    server_names = {"server", "main", "app", "index", "http", "api"}
    for name in server_names:
        for ext in [".ts", ".js", ".py", ".go", ".rs"]:
            for p in sorted(root.rglob(f"{name}{ext}")):
                rel = str(p.relative_to(root))
                # Skip node_modules, dist, etc.
                if any(part in {"node_modules", "dist", "build", "__pycache__"} for part in p.parts):
                    continue
                entries["servers"].append(rel)

    # Worker/scheduler signals
    for pattern, desc in _WORKER_SIGNALS:
        p = root / pattern
        if p.exists():
            if p.is_dir():
                for f in sorted(p.rglob("*")):
                    if f.is_file() and f.suffix in _SOURCE_EXTS:
                        entries["workers"].append(str(f.relative_to(root)))
            else:
                entries["workers"].append(str(p.relative_to(root)))

    # CLI entry points: cmd/, cli/, commands/
    for cli_dir in ["cmd", "cli", "commands"]:
        p = root / cli_dir
        if p.is_dir():
            for f in sorted(p.rglob("*.go" if cli_dir == "cmd" else "*")):
                if f.is_file():
                    entries["cli"].append(str(f.relative_to(root)))

    # Deduplicate long lists
    for key in entries:
        entries[key] = sorted(set(entries[key]))[:30]  # cap at 30

    return entries


def _count_source_files(root: Path) -> dict[str, int]:
    """Count source files by extension."""
    from collections import Counter
    counts: Counter = Counter()
    for ext in _SOURCE_EXTS:
        for p in root.rglob(f"*{ext}"):
            if any(part.startswith(".") or part in {"node_modules", "dist", "build", "__pycache__", "venv", ".git"} for part in p.parts[:-1]):
                continue
            counts[ext] += 1
    return dict(counts.most_common(20))


def _detect_runtime(root: Path) -> dict[str, Any]:
    """Heuristic runtime detection from project structure."""
    runtime: dict[str, Any] = {
        "primary_language": "unknown",
        "run_command": None,
        "build_command": None,
        "test_command": None,
    }

    # Detect primary language
    ext_counts = _count_source_files(root)
    if ext_counts:
        # Map extensions to languages
        lang_map = {
            ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript",
            ".py": "python", ".go": "go", ".rs": "rust",
            ".java": "java", ".rb": "ruby", ".php": "php",
            ".cs": "csharp", ".swift": "swift", ".kt": "kotlin",
        }
        lang_counts: dict[str, int] = {}
        for ext, count in ext_counts.items():
            lang = lang_map.get(ext, ext.lstrip("."))
            lang_counts[lang] = lang_counts.get(lang, 0) + count
        if lang_counts:
            runtime["primary_language"] = max(lang_counts, key=lambda k: lang_counts[k])

    # Detect run/build/test commands from package.json scripts
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "dev" in scripts:
                runtime["run_command"] = "npm run dev" if "dev" in scripts else None
            elif "start" in scripts:
                runtime["run_command"] = "npm start"
            if "build" in scripts:
                runtime["build_command"] = "npm run build"
            if "test" in scripts:
                runtime["test_command"] = "npm test"
        except (json.JSONDecodeError, OSError):
            pass

    # Python
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        runtime.setdefault("run_command", "python -m <module>")
        runtime.setdefault("test_command", "pytest")

    # Go
    go_mod = root / "go.mod"
    if go_mod.exists():
        runtime.setdefault("run_command", "go run .")
        runtime.setdefault("build_command", "go build .")
        runtime.setdefault("test_command", "go test ./...")

    return runtime


def inventory(root: Path) -> dict[str, Any]:
    """
    Run full project inventory.

    Returns:
        {
          "root": str,
          "manifests": {...},
          "technology": { category: [{name, evidence}] },
          "infrastructure": [{file, type}],
          "api_styles": [{style, evidence}],
          "entry_points": { servers, workers, schedulers, cli },
          "source_file_counts": { ext: count },
          "runtime": { primary_language, run_command, build_command, test_command },
          "total_source_files": int,
        }
    """
    return {
        "root": str(root),
        "manifests": _scan_manifests(root),
        "technology": _scan_fingerprints(root),
        "infrastructure": _scan_infrastructure(root),
        "api_styles": _scan_api_styles(root),
        "entry_points": _scan_entry_points(root),
        "source_file_counts": _count_source_files(root),
        "runtime": _detect_runtime(root),
        "total_source_files": sum(_count_source_files(root).values()),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="kodebrain project-inventory — architecture-aware scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root directory")
    parser.add_argument("--output", metavar="FILE", help="Write JSON to file (default: stdout)")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON (default)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    result = inventory(root)
    output = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Inventory written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
