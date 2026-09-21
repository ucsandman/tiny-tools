#!/usr/bin/env python3
"""context-budget: show where your token budget goes before you spend it.

Point it at the files and directories you are about to paste into a context
window. It reports bytes, characters, and estimated tokens per file, the
share of the total each file takes, and whether the total fits inside your
budget. Files are sorted by cost, largest first, so the first trim target
is at the top.

Token counts are estimated with the rough heuristic of 4 characters per
token. That is accurate enough to decide what to cut and what to keep;
it is not accurate enough to predict a billing invoice.

Exit status: 0 when the total fits the budget, 1 when it exceeds it, so
scripts and agents can gate on the result.

No dependencies beyond Python 3.8+. Read-only: it never modifies inputs.

Usage:
    budget.py RESUME.md docs/ transcripts/
    budget.py --budget 50000 session.md
    budget.py --budget 200000 . -o budget-report.md
"""
import argparse
import os
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             ".hg", ".svn", "dist", "build"}


def is_text(path):
    """Heuristic: a file containing a NUL byte in the first 8k is binary."""
    try:
        with open(path, "rb") as f:
            return b"\x00" not in f.read(8192)
    except OSError:
        return False


def iter_files(paths):
    seen = set()
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and not os.path.islink(os.path.join(root, d))]
                for name in files:
                    full = os.path.join(root, name)
                    real = os.path.realpath(full)
                    if real not in seen:
                        seen.add(real)
                        yield full
        else:
            print("warning: not found: %s" % p, file=sys.stderr)


def measure(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return {"path": path, "error": str(e)}
    chars = len(data.decode("utf-8", errors="replace"))
    return {
        "path": path,
        "bytes": len(data),
        "chars": chars,
        "tokens": round(chars / 4),
    }


def fmt(n):
    if n >= 1_000_000:
        return "%.1fM" % (n / 1_000_000)
    if n >= 1_000:
        return "%.1fk" % (n / 1_000)
    return str(n)


def main():
    ap = argparse.ArgumentParser(
        description="Report per-file token costs against a context budget.")
    ap.add_argument("paths", nargs="+",
                    help="files and/or directories to measure")
    ap.add_argument("--budget", type=int, default=100_000,
                    help="token budget to check against (default: 100000)")
    ap.add_argument("-o", "--output",
                    help="write the markdown report to a file instead of stdout")
    args = ap.parse_args()

    rows = []
    skipped_binary, skipped_error = 0, 0
    for path in sorted(iter_files(args.paths)):
        if not is_text(path):
            skipped_binary += 1
            continue
        r = measure(path)
        if "error" in r:
            skipped_error += 1
            print("warning: unreadable: %s (%s)" % (path, r["error"]),
                  file=sys.stderr)
            continue
        rows.append(r)

    if not rows:
        sys.exit("error: no readable text files under %s" %
                 " ".join(args.paths))

    rows.sort(key=lambda r: r["tokens"], reverse=True)
    total = sum(r["tokens"] for r in rows)

    out = []
    out.append("# Context budget report")
    out.append("")
    out.append("- Budget: ~%s tokens" % fmt(args.budget))
    out.append("- Total: ~%s tokens across %d file(s)" %
               (fmt(total), len(rows)))
    if skipped_binary:
        out.append("- Skipped %d binary file(s)" % skipped_binary)
    if skipped_error:
        out.append("- Skipped %d unreadable file(s)" % skipped_error)
    out.append("")

    out.append("## Cost per file (estimated tokens)")
    out.append("")
    out.append("| File | Tokens | Chars | Share |")
    out.append("|------|--------|-------|-------|")
    cumulative = 0
    for r in rows:
        cumulative += r["tokens"]
        rel = os.path.relpath(r["path"])
        shown = rel if not rel.startswith("..") else r["path"]
        out.append("| `%s` | ~%s | %s | %.1f%% |" %
                   (shown, fmt(r["tokens"]), fmt(r["chars"]),
                    100.0 * r["tokens"] / total if total else 0.0))
    out.append("")

    over = total > args.budget
    if over:
        out.append("## Verdict: OVER BUDGET")
        out.append("")
        out.append("Total ~%s tokens exceeds the ~%s budget by ~%s. "
                   "The largest files at the top of the table are your "
                   "first trim targets." %
                   (fmt(total), fmt(args.budget), fmt(total - args.budget)))
    else:
        out.append("## Verdict: within budget")
        out.append("")
        out.append("Total ~%s tokens fits inside the ~%s budget with ~%s "
                   "to spare." %
                   (fmt(total), fmt(args.budget), fmt(args.budget - total)))
    out.append("")
    out.append("_Token counts are estimated at 4 characters per token. "
               "Accurate enough to decide what to cut, not enough to "
               "predict a bill._")
    out.append("")

    report = "\n".join(out)
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print("wrote %s" % args.output)
    else:
        print(report)

    sys.exit(1 if over else 0)


if __name__ == "__main__":
    main()
