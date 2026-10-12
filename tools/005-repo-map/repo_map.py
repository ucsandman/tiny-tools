#!/usr/bin/env python3
"""repo-map: a one-page structural map of a codebase, as markdown.

Point it at a repo directory and it prints a markdown map: total files,
dirs, lines and a rough token estimate, a depth-limited directory tree,
the biggest files by line count, and the entry points it can detect
(READMEs, main files, package scripts, Makefile targets).

The map is meant for the start of an agent session: hand it to a new
agent so it can orient in an unfamiliar repo without spending the first
ten minutes (and ten thousand tokens) listing directories itself.

Read-only: it never writes to the scanned directory. Everything goes to
stdout, so redirect to a file or pipe it wherever you like.

Token counts use the same rough heuristic as context-budget and
context-tail: 4 characters per token. Good for sizing, not for billing.

Usage:
    repo_map.py                      # map the current directory
    repo_map.py /path/to/repo        # map another directory
    repo_map.py --depth 5 repo       # deeper tree
    repo_map.py --top 20 repo        # more "biggest files"
    repo_map.py --exclude docs repo  # also skip a directory
    repo_map.py repo > MAP.md        # save the map
"""

import argparse
import json
import os
import re
import sys

DEFAULT_DEPTH = 3
DEFAULT_TOP = 10
TOKENS_PER_CHAR = 4

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "__pycache__", ".venv", "venv", "env", ".env",
    "node_modules", "dist", "build", "target", "out", ".next",
    ".nuxt", "coverage", ".coverage", "vendor", ".idea", ".vscode",
    ".terraform", ".serverless", "Pods", "DerivedData",
}

ENTRY_FILE_NAMES = {
    "readme.md": "README",
    "license": "license",
    "licence": "license",
    "main.py": "main",
    "__main__.py": "main",
    "main.go": "main",
    "main.rs": "main",
    "index.js": "main",
    "index.ts": "main",
    "app.py": "app",
    "app.js": "app",
    "app.ts": "app",
    "manage.py": "django",
    "setup.py": "package setup",
    "pyproject.toml": "package config",
    "package.json": "package config",
    "go.mod": "module config",
    "cargo.toml": "package config",
    "gemfile": "package config",
    "composer.json": "package config",
    "requirements.txt": "dependencies",
    "dockerfile": "container",
    "docker-compose.yml": "container",
    "makefile": "build",
}


def looks_binary(path):
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def scan(root, extra_excludes):
    """Walk root; return (dirs_seen, files) where files is a list of dicts."""
    skip = SKIP_DIRS | {e.strip("/").lower() for e in extra_excludes}
    files = []
    dirs_seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in skip and not d.startswith(".egg")]
        dirs_seen += 1
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if os.path.islink(full):
                continue
            binary = looks_binary(full)
            lines = 0 if binary else count_lines(full)
            rel = os.path.relpath(full, root)
            files.append({
                "rel": rel, "name": name, "size": size,
                "lines": lines, "binary": binary,
            })
    return dirs_seen, files


def tree_lines(root, files, depth):
    """Build an indented tree up to depth levels."""
    tree = {}
    for f in files:
        parts = f["rel"].split(os.sep)
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault("__files__", []).append(parts[-1])
    lines = []
    base = os.path.abspath(root).rstrip(os.sep) + os.sep

    def emit(node, prefix, level):
        items = sorted((k, v) for k, v in node.items() if k != "__files__")
        file_list = sorted(node.get("__files__", []))
        entries = [("d", k, v) for k, v in items] + [("f", n, None) for n in file_list]
        for i, (kind, name, sub) in enumerate(entries):
            last = i == len(entries) - 1
            branch = "└── " if last else "├── "
            shown = name + ("/" if kind == "d" else "")
            lines.append(prefix + branch + shown)
            if kind == "d" and level < depth:
                emit(sub, prefix + ("    " if last else "│   "), level + 1)
        if not entries:
            lines.append(prefix + "(empty)")

    lines.append(os.path.basename(base.rstrip(os.sep)) + "/")
    emit(tree, "", 1)
    return lines


def detect_entry_points(root, files):
    points = []
    seen = set()

    def add(kind, desc):
        key = (kind, desc)
        if key not in seen:
            seen.add(key)
            points.append((kind, desc))

    for f in files:
        lower = f["name"].lower()
        if lower in ENTRY_FILE_NAMES:
            add(ENTRY_FILE_NAMES[lower], f["rel"])
        elif lower.endswith(".md") and lower.startswith("readme"):
            add("README", f["rel"])
        elif lower == "claude.md" or lower == "agents.md":
            add("agent guide", f["rel"])

    def first_file(names):
        for f in files:
            if f["name"].lower() in names:
                return os.path.join(root, f["rel"])
        return None

    pkg = first_file({"package.json"})
    if pkg:
        try:
            with open(pkg, encoding="utf-8") as fh:
                data = json.load(fh)
            for script in (data.get("scripts") or {}):
                add("npm script", "npm run " + script)
        except (OSError, ValueError):
            pass

    pyproj = first_file({"pyproject.toml"})
    if pyproj:
        try:
            with open(pyproj, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            in_scripts = False
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("[project.scripts]"):
                    in_scripts = True
                    continue
                if in_scripts:
                    if s.startswith("["):
                        break
                    m = re.match(r"([A-Za-z0-9_.-]+)\s*=", s)
                    if m:
                        add("console script", m.group(1))
        except OSError:
            pass

    make = first_file({"makefile"})
    if make:
        try:
            with open(make, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    m = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
                    if m and not m.group(1).startswith("."):
                        add("make target", "make " + m.group(1))
                        if len(points) > 30:
                            break
        except OSError:
            pass

    return points


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%d %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0


def tokens_of(chars):
    return max(1, (chars + TOKENS_PER_CHAR - 1) // TOKENS_PER_CHAR)


def main():
    ap = argparse.ArgumentParser(
        description="Print a one-page markdown map of a codebase.")
    ap.add_argument("path", nargs="?", default=".",
                    help="directory to map (default: current directory)")
    ap.add_argument("--depth", type=int, default=DEFAULT_DEPTH,
                    help="tree depth, default %d" % DEFAULT_DEPTH)
    ap.add_argument("--top", type=int, default=DEFAULT_TOP,
                    help="number of biggest files to list, default %d" % DEFAULT_TOP)
    ap.add_argument("--exclude", action="append", default=[],
                    help="extra directory name to skip (repeatable)")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print("error: not a directory: %s" % args.path, file=sys.stderr)
        return 1

    dirs_seen, files = scan(root, args.exclude)
    total_lines = sum(f["lines"] for f in files)
    total_bytes = sum(f["size"] for f in files)
    name = os.path.basename(root)

    out = []
    out.append("# repo map: %s" % name)
    out.append("")
    out.append("Generated by tiny-tools 005-repo-map. Rough token estimates "
               "use 4 chars per token, same as context-budget.")
    out.append("")
    out.append("## Totals")
    out.append("")
    out.append("- Directories: %d" % dirs_seen)
    out.append("- Files: %d (%d text, %d binary)"
               % (len(files),
                  sum(1 for f in files if not f["binary"]),
                  sum(1 for f in files if f["binary"])))
    out.append("- Lines: %d" % total_lines)
    out.append("- Size: %s" % human(total_bytes))
    out.append("- Rough whole-repo token cost: ~%d tokens"
               % tokens_of(total_bytes))
    out.append("")
    out.append("## Tree (depth %d)" % args.depth)
    out.append("")
    out.append("```")
    out.extend(tree_lines(root, files, args.depth))
    out.append("```")
    out.append("")

    biggest = sorted((f for f in files if not f["binary"]),
                     key=lambda f: f["lines"], reverse=True)[:args.top]
    if biggest:
        out.append("## Biggest files by line count")
        out.append("")
        for f in biggest:
            out.append("- `%s`: %d lines (~%d tokens)"
                       % (f["rel"], f["lines"], tokens_of(f["size"])))
        out.append("")

    points = detect_entry_points(root, files)
    if points:
        out.append("## Entry points detected")
        out.append("")
        for kind, desc in points:
            out.append("- **%s**: `%s`" % (kind, desc))
        out.append("")

    print("\n".join(out).rstrip() + "\n")
    print("repo-map: %d files, %d lines, ~%d tokens for %s"
          % (len(files), total_lines, tokens_of(total_bytes), name),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
