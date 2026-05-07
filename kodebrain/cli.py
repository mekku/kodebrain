"""
kodebrain CLI — install agent instructions and git hooks.

Usage:
  kodebrain install [path] [--platform all|claude|cursor|copilot|windsurf|cline]
  kodebrain uninstall [path]
  kodebrain hook install [path]
  kodebrain hook uninstall [path]
  kodebrain hook status [path]
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from kodebrain.install import PLATFORMS, install, uninstall
from kodebrain import hook as _hook


ALL_PLATFORMS = list(PLATFORMS.keys())


def cmd_install(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    platforms = ALL_PLATFORMS if args.platform == "all" else [args.platform]

    try:
        written = install(root, platforms)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Kode Brain installed in {root.name}/")
    for f in written:
        label = next(
            (PLATFORMS[p]["label"] for p in PLATFORMS if PLATFORMS[p]["file"] == f),
            f,
        )
        print(f"  ✓ {f}  ({label})")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    changed = uninstall(root)

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
    p_install = sub.add_parser("install", help="Write KB instruction blocks to platform config files.")
    p_install.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")
    p_install.add_argument(
        "--platform",
        choices=["all"] + ALL_PLATFORMS,
        default="all",
        help="Target platform (default: all)",
    )

    # uninstall
    p_uninstall = sub.add_parser("uninstall", help="Remove all KB instruction blocks.")
    p_uninstall.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")

    # hook
    p_hook = sub.add_parser("hook", help="Manage the git post-commit hook.")
    hook_sub = p_hook.add_subparsers(dest="hook_cmd", required=True)
    for hcmd in ("install", "uninstall", "status"):
        hp = hook_sub.add_parser(hcmd)
        hp.add_argument("path", nargs="?", default=".", help="Project root (default: current directory)")

    args = parser.parse_args()

    if args.command == "install":
        sys.exit(cmd_install(args))
    elif args.command == "uninstall":
        sys.exit(cmd_uninstall(args))
    elif args.command == "hook":
        sys.exit(cmd_hook(args))


if __name__ == "__main__":
    main()
