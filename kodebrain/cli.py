"""
kodebrain CLI — install agent instructions and git hooks.

Usage:
  kodebrain install                          # user-level: global config dirs (~/.claude/CLAUDE.md etc.)
  kodebrain install <path>                   # project-level: writes to project config files
  kodebrain install [path] --platform <p>    # specific platform only
  kodebrain uninstall                        # remove user-level blocks
  kodebrain uninstall <path>                 # remove project-level blocks
  kodebrain hook install [path]
  kodebrain hook uninstall [path]
  kodebrain hook status [path]
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from kodebrain.install import (
    PROJECT_PLATFORMS,
    USER_PLATFORMS,
    install_project,
    install_user,
    uninstall_project,
    uninstall_user,
)
from kodebrain import hook as _hook

ALL_PROJECT_PLATFORMS = list(PROJECT_PLATFORMS.keys())  # claude cursor copilot windsurf cline codex opencode
ALL_USER_PLATFORMS = list(USER_PLATFORMS.keys())        # claude cursor windsurf cline codex opencode


def cmd_install(args: argparse.Namespace) -> int:
    user_mode = args.path is None

    if user_mode:
        platforms = ALL_USER_PLATFORMS if args.platform == "all" else [args.platform]
        # filter out platforms not supported at user level
        platforms = [p for p in platforms if p in USER_PLATFORMS]
        written = install_user(platforms)
        print("Kode Brain installed (user-level)")
        for f in written:
            label = USER_PLATFORMS.get(
                next((p for p in USER_PLATFORMS if str(Path.home() / USER_PLATFORMS[p]["file"]) == f), ""),
                {},
            ).get("label", f)
            print(f"  ✓ {f}  ({label})")
        print()
        print("Every project you open will now be checked for a Kode Brain KB.")
    else:
        root = Path(args.path).resolve()
        platforms = ALL_PROJECT_PLATFORMS if args.platform == "all" else [args.platform]
        try:
            written = install_project(root, platforms)
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"Kode Brain installed in {root.name}/")
        for f, note in written:
            label = next(
                (PROJECT_PLATFORMS[p]["label"] for p in PROJECT_PLATFORMS
                 if PROJECT_PLATFORMS[p]["file"] == f),
                f,
            )
            print(f"  ✓ {f}  ({label})")
            if note:
                for line in note.splitlines():
                    print(f"    {line}")

    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    user_mode = args.path is None

    if user_mode:
        changed = uninstall_user()
        if not changed:
            print("No user-level Kode Brain blocks found — nothing to remove.")
            return 0
        print("Kode Brain removed (user-level)")
        for f in changed:
            print(f"  ✓ {f}")
    else:
        root = Path(args.path).resolve()
        changed = uninstall_project(root)
        if not changed:
            print("No Kode Brain blocks found — nothing to remove.")
            return 0
        print(f"Kode Brain removed from {root.name}/")
        for f in changed:
            print(f"  ✓ {f}")

    return 0


def cmd_hook(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()

    if not (root / ".git").is_dir():
        print(f"error: {root} is not a git repository.", file=sys.stderr)
        return 1

    if args.hook_cmd == "install":
        path = _hook.install(root)
        print(f"Hook installed: {path}")
    elif args.hook_cmd == "uninstall":
        removed = _hook.uninstall(root)
        print("Hook removed." if removed else "Hook not installed — nothing to remove.")
    elif args.hook_cmd == "status":
        installed = _hook.status(root)
        print(f"Hook {'installed' if installed else 'not installed'}.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kodebrain",
        description="Kode Brain — install agent instructions across AI platforms.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # install
    p_install = sub.add_parser(
        "install",
        help="Write KB instructions. No path = user-level (global). Path = project-level.",
    )
    p_install.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Project root for project-level install. Omit for user-level (global).",
    )
    p_install.add_argument(
        "--platform",
        choices=["all"] + ALL_PROJECT_PLATFORMS,
        default="all",
        help="Target platform (default: all)",
    )

    # uninstall
    p_uninstall = sub.add_parser(
        "uninstall",
        help="Remove KB blocks. No path = user-level. Path = project-level.",
    )
    p_uninstall.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Project root for project-level uninstall. Omit for user-level.",
    )

    # hook
    p_hook = sub.add_parser("hook", help="Manage the git post-commit hook.")
    hook_sub = p_hook.add_subparsers(dest="hook_cmd", required=True)
    for hcmd in ("install", "uninstall", "status"):
        hp = hook_sub.add_parser(hcmd)
        hp.add_argument("path", nargs="?", default=".", help="Project root (default: .)")

    args = parser.parse_args()

    if args.command == "install":
        sys.exit(cmd_install(args))
    elif args.command == "uninstall":
        sys.exit(cmd_uninstall(args))
    elif args.command == "hook":
        sys.exit(cmd_hook(args))


if __name__ == "__main__":
    main()
