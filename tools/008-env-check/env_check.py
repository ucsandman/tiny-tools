#!/usr/bin/env python3
"""env-check: find the environment variables a codebase needs.

Point it at a directory (or run it inside one) and it prints a markdown
report of every environment variable referenced in the code: shell
$VAR and ${VAR}, Python os.environ / os.getenv, and JavaScript
process.env. Each variable is marked set or unset against the current
environment, and any default found in the code is shown.

Handy at the start of a session in an unfamiliar repo, when the README
says "set your env vars" but never says which ones. It answers two
questions: what does this code expect, and what is missing here.

It only reads files, it never writes to the scanned tree. References in
comments and strings count the same as references in code, because
telling them apart per language would make this a parser, not a tiny
tool. Binary files are skipped, and so are .git, node_modules,
__pycache__, .venv, dist, and build directories.

Usage:
    env_check.py                   # scan the current directory
    env_check.py /path/to/repo     # scan another directory
    env_check.py --unset-only repo # show only variables not set here
"""

import argparse
import os
import re
import sys

# Each pattern yields (variable name, default value or None).
PATTERNS = (
    # ${VAR}, ${VAR:-default}, ${VAR-default}, ${VAR:?msg}
    re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::?[-?+]([^}]*))?\}"),
    # $VAR, but not $$, $1, $@, or $VAR inside ${...} (handled above)
    re.compile(r"(?<![${])\$([A-Za-z_][A-Za-z0-9_]*)"),
    # os.environ["VAR"]
    re.compile(r"os\.environ\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]"),
    # os.environ.get("VAR", default), os.getenv("VAR", default)
    re.compile(r"os\.environ\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
               r"(?:\s*,\s*([^)]*?))?\s*\)"),
    re.compile(r"os\.getenv\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"
               r"(?:\s*,\s*([^)]*?))?\s*\)"),
    # process.env.VAR and process.env["VAR"]
    re.compile(r"process\.env\.([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"process\.env\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]"),
)

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".tox", ".eggs",
}


def is_binary(path):
    try:
        with open(path, "rb") as handle:
            chunk = handle.read(1024)
    except OSError:
        return True
    return b"\0" in chunk


def scan(root):
    """Walk root, return (vars, files_scanned). vars maps a name to a
    dict with keys: files (set of relpaths), defaults (set of strings).
    """
    found = {}
    files_scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if is_binary(path):
                continue
            try:
                with open(path, "r", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            files_scanned += 1
            relpath = os.path.relpath(path, root)
            for pattern in PATTERNS:
                for match in pattern.finditer(text):
                    var = match.group(1)
                    default = None
                    if match.lastindex and match.lastindex >= 2:
                        default = (match.group(2) or "").strip()
                        if default:
                            default = default.strip("\"'")
                    entry = found.setdefault(var, {"files": set(),
                                                   "defaults": set()})
                    entry["files"].add(relpath)
                    if default:
                        entry["defaults"].add(default)
    return found, files_scanned


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report the environment variables a codebase "
                    "references, and which are unset here.")
    parser.add_argument("path", nargs="?", default=".",
                        help="directory to scan (default: current)")
    parser.add_argument("--unset-only", action="store_true",
                        help="show only variables not set in this "
                             "environment")
    args = parser.parse_args(argv)

    root = args.path
    if not os.path.isdir(root):
        print(f"env-check: not a directory: {root}", file=sys.stderr)
        return 1

    found, files_scanned = scan(root)
    rows = []
    for var in sorted(found):
        entry = found[var]
        status = "set" if var in os.environ else "UNSET"
        if args.unset_only and status == "set":
            continue
        defaults = "; ".join(sorted(entry["defaults"]))
        files = ", ".join(sorted(entry["files"]))
        rows.append((var, status, defaults, files))

    n_set = sum(1 for var in found if var in os.environ)
    print(f"# env-check: {root}", file=sys.stderr)
    print(f"# {len(found)} variables referenced in {files_scanned} files; "
          f"{n_set} set, {len(found) - n_set} unset here", file=sys.stderr)

    print(f"# Environment variables referenced in `{root}`")
    print()
    if not rows:
        print("No environment variable references found."
              if not args.unset_only
              else "Every referenced variable is set here.")
        return 0
    print("| Variable | Here | Default | Referenced in |")
    print("|----------|------|---------|---------------|")
    for var, status, defaults, files in rows:
        print(f"| `{var}` | {status} | {defaults} | {files} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
