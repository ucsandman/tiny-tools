#!/usr/bin/env python3
"""handoff-note: turn a git repo's current state into a markdown context note.

Read-only against the repo. Writes the note to stdout, or to a file with -o.
No dependencies beyond Python 3.8+ and git.

Usage:
    handoff.py [repo_path] [-o note.md]
"""
import argparse
import datetime
import subprocess
import sys


def git(repo, *args):
    # Note: stdout is NOT stripped here. Callers strip what they need, because
    # `git status --porcelain` encodes meaning in leading whitespace.
    p = subprocess.run(["git", "-C", repo, *args],
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ""


def main():
    ap = argparse.ArgumentParser(
        description="Generate a markdown handoff note from a git repo's state.")
    ap.add_argument("repo", nargs="?", default=".",
                    help="path to the git repo (default: current directory)")
    ap.add_argument("-o", "--output",
                    help="write the note to a file instead of stdout")
    args = ap.parse_args()

    if not git(args.repo, "rev-parse", "--git-dir").strip():
        sys.exit("error: not a git repo: %s" % args.repo)

    toplevel = git(args.repo, "rev-parse", "--show-toplevel").strip()
    name = toplevel.rsplit("/", 1)[-1] if toplevel else args.repo
    branch = git(args.repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    today = datetime.date.today().isoformat()

    staged, unstaged, untracked = [], [], []
    for line in git(args.repo, "status", "--porcelain").splitlines():
        code, path = line[:2], line[3:]
        if code == "??":
            untracked.append(path)
        else:
            if code[0] != " ":
                staged.append((code[0], path))
            if code[1] != " ":
                unstaged.append((code[1], path))

    diffstat = git(args.repo, "diff", "--stat", "HEAD").strip("\n")
    log = git(args.repo, "log", "--oneline", "-8").strip("\n")
    stash = git(args.repo, "stash", "list").strip("\n")

    out = []
    out.append("# Handoff note: %s" % name)
    out.append("")
    out.append("Date: %s" % today)
    out.append("Branch: `%s`" % branch)
    out.append("")

    out.append("## Working tree")
    out.append("")
    if staged:
        out.append("### Staged")
        out.extend("- `%s` %s" % (c, p) for c, p in staged)
        out.append("")
    if unstaged:
        out.append("### Unstaged")
        out.extend("- `%s` %s" % (c, p) for c, p in unstaged)
        out.append("")
    if untracked:
        out.append("### Untracked")
        out.extend("- %s" % p for p in untracked)
        out.append("")
    if not (staged or unstaged or untracked):
        out.append("Clean. Nothing staged, unstaged, or untracked.")
        out.append("")

    out.append("## Diff stat (working tree vs HEAD)")
    out.append("")
    out.append("```")
    out.append(diffstat if diffstat else "(no differences)")
    out.append("```")
    out.append("")

    out.append("## Recent commits")
    out.append("")
    out.append("```")
    out.append(log if log else "(no commits yet)")
    out.append("```")
    out.append("")

    if stash:
        out.append("## Stash")
        out.append("")
        out.append("```")
        out.append(stash)
        out.append("```")
        out.append("")

    out.append("## Fill in before handing off")
    out.append("")
    out.append("- What I did:")
    out.append("- What's next:")
    out.append("- Watch out for:")
    out.append("- How to verify:")
    out.append("")

    note = "\n".join(out)
    if args.output:
        with open(args.output, "w") as f:
            f.write(note)
        print("wrote %s" % args.output)
    else:
        print(note)


if __name__ == "__main__":
    main()
