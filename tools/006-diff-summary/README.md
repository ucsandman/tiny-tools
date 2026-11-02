# 006: diff-summary

A tiny script that turns a git diff into a readable markdown summary:
totals, a per-file table of insertions and deletions, and for each text
file the most telling added and removed lines (deduped and capped), so
you can see the shape of a change without reading the whole patch. Run
it before you commit, paste it into a handoff note or a PR description,
or hand it to an agent so it can answer "what changed here" without
burning the entire diff as context.

## Why it exists

A raw `git diff` is the most honest record of what changed, and the
least skimmable: thousands of lines of +/- when you only want the gist.
`git diff --stat` gives you counts but no content; reading the full
patch gives you content but no summary. diff-summary sits in between.
It keeps the file-by-file shape, shows a few representative lines per
file so you can tell a refactor from a feature from a dependency bump,
and marks the cut where it stops showing lines. It is read-only: it
runs `git diff` and prints markdown, it never touches the working tree.

## Usage

```bash
# summarize unstaged changes in the current repo
python3 diff_summary.py

# summarize staged changes
python3 diff_summary.py --staged

# summarize changes against a branch
python3 diff_summary.py --base main

# run against another repo
python3 diff_summary.py /path/to/repo

# more sample lines per file per side
python3 diff_summary.py --max-lines 20 repo

# save it or pipe it onward
python3 diff_summary.py repo > CHANGES.md
```

Read-only against the scanned repo, always. No dependencies beyond
Python 3.8+ and a git binary. A one-line summary goes to stderr; the
markdown goes to stdout. Exit status is 0 on success, 1 if the path is
not inside a git working tree or `git diff` fails.

## What it does

- Summarizes unstaged changes by default, `--staged` for the index,
  `--base <ref>` to diff against a branch, tag, or commit
- Prints totals (files changed, insertions, deletions) and a per-file
  table, so the shape of the change is visible at a glance
- For each text file, shows up to `--max-lines` (default 10) distinct
  added and removed lines, most interesting first, and says how many
  more exist, so the sample is honest about the cut
- Handles new files, deleted files, renames, and binary files (marked
  as binary, content not shown)

## What it deliberately does not do

- No semantic diffing: it does not know that a function moved; it shows
  added and removed lines, and the agent still interprets what they mean
- No git history: commit-by-commit breakdowns are handoff-note's job
- No syntax-aware highlighting or per-function attribution: keeping it
  language-agnostic is the point; one file, no dependencies
- No word-level or side-by-side view: that is a diff viewer, not a tiny tool
