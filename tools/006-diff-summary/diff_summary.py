#!/usr/bin/env python3
"""diff-summary: turn a git diff into a readable markdown summary.

Point it at a git repo (or run it inside one) and it prints a markdown
summary of what changed: totals, a per-file table of insertions and
deletions, and for each text file the most interesting added and removed
lines (deduped, capped), so a human or agent can see the shape of the
change without reading the whole patch.

It reads `git diff` output, it never touches the working tree. Handy
for handoff notes, PR descriptions, and sanity checks before a commit.

Usage:
    diff_summary.py                      # summarize unstaged changes
    diff_summary.py --staged             # summarize staged changes
    diff_summary.py --base main          # summarize changes vs a ref
    diff_summary.py /path/to/repo       # run against another repo
    diff_summary.py --max-lines 20 repo  # more sample lines per file
"""

import argparse
import re
import subprocess
import sys

DEFAULT_MAX_LINES = 10

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

def git_diff(repo, mode_args):
    proc = subprocess.run(
        ["git", "diff", "--no-color", "--no-ext-diff", "-U0"] + mode_args,
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(
            "git diff failed: " + (proc.stderr.strip() or "exit %d" % proc.returncode)
        )
    return proc.stdout

def check_repo(repo):
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or proc.stdout.strip() != "true":
        raise RuntimeError("not inside a git working tree: " + repo)

def parse_diff(text, max_lines):
    """Return a list of file dicts in diff order."""
    files = []
    cur = None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            parts = line.split(" ", 3)
            a, b = parts[2], parts[3]
            old = a[2:] if a.startswith("a/") else a
            new = b[2:] if b.startswith("b/") else b
            cur = {
                "old": old, "new": new,
                "added": 0, "removed": 0,
                "added_lines": [], "removed_lines": [],
                "added_extra": 0, "removed_extra": 0,
                "binary": False, "new_file": False, "deleted": False,
                "added_seen": set(), "removed_seen": set(),
            }
            files.append(cur)
        elif cur is None:
            continue
        elif line.startswith("Binary files"):
            cur["binary"] = True
        elif line.startswith("new file mode"):
            cur["new_file"] = True
        elif line.startswith("deleted file mode"):
            cur["deleted"] = True
        elif line.startswith("rename from"):
            cur["old"] = line.split(" ", 2)[2]
        elif line.startswith("rename to"):
            cur["new"] = line.split(" ", 2)[2]
        elif line.startswith("+") and not line.startswith("+++"):
            cur["added"] += 1
            record_line(cur, "added", line[1:], max_lines)
        elif line.startswith("-") and not line.startswith("---"):
            cur["removed"] += 1
            record_line(cur, "removed", line[1:], max_lines)

    def label(f):
        if f["old"] == f["new"]:
            return f["new"]
        return "%s -> %s" % (f["old"], f["new"])

    for f in files:
        f["label"] = label(f)
        del f["added_seen"]
        del f["removed_seen"]
    return files

def record_line(cur, side, line, max_lines):
    stripped = line.strip()
    if not stripped:
        return
    key = "added" if side == "added" else "removed"
    seen_key = key + "_seen"
    if stripped in cur[seen_key]:
        cur[key + "_extra"] += 1
        return
    if len(cur[key + "_lines"]) < max_lines:
        cur[key + "_lines"].append(stripped)
        cur[seen_key].add(stripped)
    else:
        cur[key + "_extra"] += 1

def escape(text):
    return text.replace("|", "\\|")

def render(files, describe, max_lines):
    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)
    out = []
    out.append("# diff-summary: %s" % describe)
    out.append("")
    if not files:
        out.append("No changes.")
        return "\n".join(out) + "\n"
    out.append("%d file%s changed, +%d / -%d" % (
        len(files), "s" if len(files) != 1 else "", total_added, total_removed))
    out.append("")
    out.append("| File | + | - |")
    out.append("|------|---|-|")
    for f in files:
        note = ""
        if f["binary"]:
            note = " (binary)"
        elif f["new_file"]:
            note = " (new)"
        elif f["deleted"]:
            note = " (deleted)"
        out.append("| %s%s | %d | %d |" % (escape(f["label"]), note, f["added"], f["removed"]))
    out.append("")
    for f in files:
        out.append("## %s" % escape(f["label"]))
        out.append("")
        if f["binary"]:
            out.append("_Binary file, content not shown._")
            out.append("")
            continue
        status = []
        if f["new_file"]:
            status.append("new file")
        if f["deleted"]:
            status.append("deleted")
        if status:
            out.append("_%s, +%d / -%d._" % ("; ".join(status), f["added"], f["removed"]))
            out.append("")
        if f["added_lines"]:
            out.append("Added:")
            for line in f["added_lines"]:
                out.append("+ " + line)
            if f["added_extra"]:
                out.append("... +%d more added lines" % f["added_extra"])
        if f["removed_lines"]:
            out.append("Removed:")
            for line in f["removed_lines"]:
                out.append("- " + line)
            if f["removed_extra"]:
                out.append("... -%d more removed lines" % f["removed_extra"])
        if not f["added_lines"] and not f["removed_lines"]:
            out.append("_Mode or rename only, no content change._")
        out.append("")
    return "\n".join(out).rstrip() + "\n"

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Summarize a git diff as readable markdown.")
    parser.add_argument("repo", nargs="?", default=".",
                        help="git repo to inspect (default: current dir)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true",
                       help="summarize staged changes instead of unstaged")
    group.add_argument("--base", metavar="REF",
                       help="summarize changes against a branch/tag/commit")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES,
                        help="sample lines shown per file per side (default 10)")
    args = parser.parse_args(argv)

    try:
        check_repo(args.repo)
        mode_args = []
        if args.staged:
            mode_args = ["--cached"]
            describe = "staged changes"
        elif args.base:
            mode_args = [args.base]
            describe = "changes against %s" % args.base
        else:
            describe = "unstaged changes"
        files = parse_diff(git_diff(args.repo, mode_args), args.max_lines)
    except RuntimeError as e:
        sys.stderr.write("diff-summary: %s\n" % e)
        return 1

    sys.stdout.write(render(files, describe, args.max_lines))
    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)
    sys.stderr.write("diff-summary: %d files, +%d / -%d (%s)\n" % (
        len(files), total_added, total_removed, describe))
    return 0

if __name__ == "__main__":
    sys.exit(main())
