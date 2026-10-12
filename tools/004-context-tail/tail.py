#!/usr/bin/env python3
"""context-tail: trim a log or transcript down to a token budget.

Agent developers paste logs and session transcripts into context windows.
Those files always grow longer than the budget. This keeps the most recent
lines that fit inside your token budget and marks exactly what was cut, so
the reader knows the beginning is missing instead of wondering.

Token counts use the same rough heuristic as context-budget: 4 characters
per token. Accurate enough to size a paste, not enough to predict a bill.

Exit status is always 0. A one-line summary goes to stderr; the trimmed
text goes to stdout (or -o).

No dependencies beyond Python 3.8+. Read-only against the input unless
you pass -o.

Usage:
    tail.py session-log.txt
    tail.py --budget 5000 debug-output.txt
    tail.py < pasted-log.txt
    tail.py -o trimmed.txt huge.log
"""
import argparse
import sys

DEFAULT_BUDGET = 20_000
TOKENS_PER_CHAR = 4
MARKER_RESERVE = 50  # rough cost of the trim marker itself


def tokens_of(text):
    return max(1, (len(text) + TOKENS_PER_CHAR - 1) // TOKENS_PER_CHAR)


def read_input(path):
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as f:
            data = f.read()
    return data.decode("utf-8", errors="replace")


def trim(text, budget):
    """Keep the most recent lines that fit inside the budget.

    Returns (trimmed_lines, dropped_lines, dropped_tokens). If everything
    fits, dropped_lines is 0 and no marker is added.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]  # trailing newline is not a line

    total = tokens_of(text)
    if total <= budget:
        return lines, 0, 0

    room = max(budget - MARKER_RESERVE, 1)
    kept = []
    kept_tokens = 0
    for line in reversed(lines):
        cost = tokens_of(line) + 1  # +1 for the newline
        if kept_tokens + cost > room:
            break
        kept.append(line)
        kept_tokens += cost
    kept.reverse()

    if not kept:
        # One enormous line beats the whole budget. Keep the last line
        # anyway: a partial answer beats an empty one.
        kept = [lines[-1]]

    dropped = len(lines) - len(kept)
    dropped_tokens = total - tokens_of("\n".join(kept))
    return kept, dropped, dropped_tokens


def main():
    ap = argparse.ArgumentParser(
        description="Keep the most recent lines of a log that fit inside "
                    "a token budget.")
    ap.add_argument("input", nargs="?", default="-",
                    help="input file (default: stdin)")
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                    help="token budget to fit inside (default: %d)"
                    % DEFAULT_BUDGET)
    ap.add_argument("--marker",
                    help="custom trim-marker line (supports {lines} and "
                         "{tokens} placeholders)")
    ap.add_argument("-o", "--output",
                    help="write the trimmed text to a file instead of stdout")
    args = ap.parse_args()

    try:
        text = read_input(args.input)
    except OSError as e:
        sys.exit("error: cannot read %s (%s)" % (args.input, e))

    kept, dropped, dropped_tokens = trim(text, args.budget)
    total_tokens = tokens_of(text)

    out_lines = list(kept)
    if dropped:
        if args.marker:
            marker = args.marker.format(lines=dropped, tokens=dropped_tokens)
        else:
            marker = ("[... trimmed %d older line(s), ~%d token(s), "
                      "to fit a ~%d-token budget ...]"
                      % (dropped, dropped_tokens, args.budget))
        out_lines.insert(0, marker)

    result = "\n".join(out_lines) + ("\n" if out_lines else "")

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print("wrote %s" % args.output, file=sys.stderr)
    else:
        sys.stdout.write(result)

    if dropped:
        print("context-tail: kept %d of %d lines (~%d of ~%d tokens) "
              "within a ~%d-token budget" %
              (len(kept), len(kept) + dropped,
               tokens_of("\n".join(kept)),
               tokens_of("\n".join(kept)) + dropped_tokens,
               args.budget), file=sys.stderr)
    else:
        if total_tokens > args.budget:
            print("context-tail: budget ~%d exceeded by a single oversized "
                  "line (~%d tokens); kept it whole, nothing to trim"
                  % (args.budget, total_tokens), file=sys.stderr)
        else:
            print("context-tail: no trimming needed (%d line(s), ~%d tokens, "
                  "budget ~%d)" %
                  (len(kept), total_tokens, args.budget), file=sys.stderr)


if __name__ == "__main__":
    main()
