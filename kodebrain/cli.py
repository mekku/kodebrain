"""
kodebrain CLI — install Kode Brain skill and project configs across AI platforms.

Usage:
  kodebrain install [--platform all|claude|cursor|windsurf|cline|codex|opencode]
  kodebrain uninstall [--platform ...]

  kodebrain claude   install [path]
  kodebrain cursor   install [path]
  kodebrain copilot  install [path]
  kodebrain windsurf install [path]
  kodebrain cline    install [path]
  kodebrain codex    install [path]
  kodebrain opencode install [path]

  kodebrain <platform> uninstall [path]

  kodebrain hook install   [path]
  kodebrain hook uninstall [path]
  kodebrain hook status    [path]
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from kodebrain.install import (
    install_global,
    uninstall_global,
    install_project,
    uninstall_project,
)
from kodebrain import hook as _hook

GLOBAL_PLATFORMS = ["claude", "cursor", "windsurf", "cline", "codex", "opencode"]
PROJECT_PLATFORMS = ["claude", "cursor", "copilot", "windsurf", "cline", "codex", "opencode"]


def cmd_global_install(args: argparse.Namespace) -> int:
    platforms = GLOBAL_PLATFORMS if args.platform == "all" else [args.platform]
    results = install_global(platforms)
    print("Kode Brain installed (global)")
    for label, path in results:
        print(f"  ✓ {path}  ({label})")
    print()
    print("Skill installed. Open a project and run /kodebrain init to build a knowledge map.")
    return 0


def cmd_global_uninstall(args: argparse.Namespace) -> int:
    platforms = GLOBAL_PLATFORMS if args.platform == "all" else [args.platform]
    changed = uninstall_global(platforms)
    if not changed:
        print("No global Kode Brain skill found — nothing to remove.")
        return 0
    print("Kode Brain removed (global)")
    for path in changed:
        print(f"  ✓ {path}")
    return 0


def cmd_project_install(platform: str, args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    try:
        rel_path, note = install_project(root, platform)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"  ✓ {rel_path}")
    if note:
        for line in note.splitlines():
            print(f"    {line}")
    return 0


def cmd_project_uninstall(platform: str, args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    result = uninstall_project(root, platform)
    if result is None:
        print("No Kode Brain block found — nothing to remove.")
        return 0
    print(f"  ✓ {result}")
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
        description="Kode Brain — install AI skill and project configs across platforms.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Global: kodebrain install / uninstall
    p_install = sub.add_parser(
        "install",
        help="Install Kode Brain skill globally to platform dirs.",
    )
    p_install.add_argument(
        "--platform",
        choices=["all"] + GLOBAL_PLATFORMS,
        default="all",
        help="Target platform (default: all)",
    )

    p_uninstall = sub.add_parser(
        "uninstall",
        help="Remove globally installed Kode Brain skill.",
    )
    p_uninstall.add_argument(
        "--platform",
        choices=["all"] + GLOBAL_PLATFORMS,
        default="all",
        help="Target platform (default: all)",
    )

    # Per-platform project sub-commands
    for platform in PROJECT_PLATFORMS:
        pp = sub.add_parser(platform, help=f"Manage Kode Brain project config for {platform}.")
        pp_sub = pp.add_subparsers(dest=f"{platform}_cmd", required=True)

        pi = pp_sub.add_parser("install", help=f"Write ## Kode Brain to {platform} project config.")
        pi.add_argument("path", nargs="?", default=".", help="Project root (default: .)")

        pu = pp_sub.add_parser("uninstall", help=f"Remove ## Kode Brain from {platform} project config.")
        pu.add_argument("path", nargs="?", default=".", help="Project root (default: .)")

    # Hook
    p_hook = sub.add_parser("hook", help="Manage the git post-commit hook.")
    hook_sub = p_hook.add_subparsers(dest="hook_cmd", required=True)
    for hcmd in ("install", "uninstall", "status"):
        hp = hook_sub.add_parser(hcmd)
        hp.add_argument("path", nargs="?", default=".", help="Project root (default: .)")

    args = parser.parse_args()

    if args.command == "install":
        sys.exit(cmd_global_install(args))
    elif args.command == "uninstall":
        sys.exit(cmd_global_uninstall(args))
    elif args.command in PROJECT_PLATFORMS:
        platform = args.command
        sub_cmd = getattr(args, f"{platform}_cmd")
        if sub_cmd == "install":
            sys.exit(cmd_project_install(platform, args))
        elif sub_cmd == "uninstall":
            sys.exit(cmd_project_uninstall(platform, args))
    elif args.command == "hook":
        sys.exit(cmd_hook(args))


if __name__ == "__main__":
    main()
