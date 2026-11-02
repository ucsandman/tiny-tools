#!/usr/bin/env python3
"""todo-scan: find unfinished work markers in a codebase.

Point it at a directory (or run it inside one) and it prints a markdown
report of TODO, FIXME, XXX, and HACK markers: a per-tag count, a
per-file table, and every match as file:line with the matching text.
Handy at the start of a session, when you want to know what the last
session left unfinished without grepping through the whole tree.

It only reads files, it never writes to the scanned tree. Markers are
matched case-sensitively as whole words, so "methodology" does not
count but "TODO: fix this" does. Binary files are skipped, and so are
.git, node_modules, __pycache__, .venv, dist, and build directories.

Usage:
    todo_scan.py                   # scan the current directory
    todo_scan.py /path/to/repo     # scan another directory
    todo_scan.py --tag FIXME repo  # only FIXME markers
    todo_scan.py --max 200 repo    # cap the matches shown
"""

import argparse
import os
import re
import sys

TAGS = ("TODO", "FIXME", "XXX", "HACK")
TAG_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".tox", ".eggs"}
DEFAULT_MAX = 500


def is_binary(path):
    try:
        with open(path, "rb") as handle:
            chunk = handle.read(1024)
    except OSError:
        return True
    return b"\0" in chunk


def scan(root, wanted):
    """Walk root, return (matches, files_scanned). A match is
    (relpath, lineno, tag, text)."""
    matches = []
    files_scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if is_binary(path):
                continue
            files_scanned += 1
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    lines = handle.readlines()
            except OSError:
                continue
            relpath = os.path.relpath(path, root)
            for lineno, line in enumerate(lines, 1):
                found = TAG_RE.search(line)
                if found and found.group(1) in wanted:
                    matches.append((relpath, lineno, found.group(1),
                                    line.strip()))
    return matches, files_scanned


def render(root, matches, files_scanned, max_shown):
    out = ["# todo-scan: %s" % os.path.abspath(root), ""]
    out.append("%d marker(s) in %d file(s) scanned." % (len(matches),
                                                         files_scanned))
    out.append("")
    if not matches:
        out.append("No unfinished work markers found. Enjoy the clean tree.")
        return "\n".join(out) + "\n"
    counts = {}
    for _, _, tag, _ in matches:
        counts[tag] = counts.get(tag, 0) + 1
    out.append("## By tag")
    out.append("")
    for tag in TAGS:
        if tag in counts:
            out.append("- %s: %d" % (tag, counts[tag]))
    out.append("")
    per_file = {}
    for relpath, _, _, _ in matches:
        per_file[relpath] = per_file.get(relpath, 0) + 1
    out.append("## By file")
    out.append("")
    out.append("| File | Markers |")
    out.append("|------|---------|")
    for relpath, count in sorted(per_file.items(),
                                 key=lambda item: (-item[1], item[0])):
        out.append("| %s | %d |" % (relpath, count))
    out.append("")
    out.append("## Matches")
    out.append("")
    shown = matches[:max_shown]
    for relpath, lineno, tag, text in shown:
        out.append("- `%s:%d` **%s** %s" % (relpath, lineno, tag, text))
    if len(matches) > max_shown:
        out.append("")
        out.append("... and %d more match(es) not shown "
                   "(raise --max to see them)." % (len(matches) - max_shown))
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find TODO/FIXME/XXX/HACK markers in a codebase.")
    parser.add_argument("path", nargs="?", default=".",
                        help="directory to scan (default: current directory)")
    parser.add_argument("--tag", choices=TAGS, action="append", default=None,
                        help="only report this tag (repeatable)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help="max matches shown (default: %d)" % DEFAULT_MAX)
    args = parser.parse_args(argv)
    root = args.path
    if not os.path.isdir(root):
        print("todo-scan: not a directory: %s" % root, file=sys.stderr)
        return 1
    wanted = set(args.tag) if args.tag else set(TAGS)
    matches, files_scanned = scan(root, wanted)
    sys.stdout.write(render(root, matches, files_scanned, args.max))
    print("todo-scan: %d marker(s) in %d file(s)" % (len(matches),
                                                      files_scanned),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
