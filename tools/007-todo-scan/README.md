# 007: todo-scan

A tiny script that finds unfinished work markers in a codebase: TODO,
FIXME, XXX, and HACK, reported as a markdown list of file:line matches
with per-tag counts and a per-file table. Run it at the start of a
session to see what the last session left unfinished, before you decide
what to work on.

## Why it exists

Every codebase accumulates markers for work someone meant to come back
to, and they scatter: a TODO in one file, a FIXME three directories
over, a HACK nobody remembers writing. Grep finds them, but grep gives
you raw lines with no shape: no counts, no per-file summary, nothing
you can paste into a session note. todo-scan is the boring version of
the job: one command, a counted report, every match located. It pairs
with repo-map (the shape of the codebase) and handoff-note (where the
last session stopped): repo-map says what exists, todo-scan says what
is unfinished.

## Usage

```bash
# scan the current directory
python3 todo_scan.py

# scan another directory
python3 todo_scan.py /path/to/repo

# only FIXME markers
python3 todo_scan.py --tag FIXME repo

# cap the matches shown (default 500)
python3 todo_scan.py --max 50 repo

# save it or pipe it onward
python3 todo_scan.py repo > UNFINISHED.md
```

Read-only against the scanned tree, always. No dependencies beyond
Python 3.8+. A one-line summary goes to stderr; the markdown goes to
stdout. Exit status is 0 on success, 1 if the path is not a directory.

## What it does

- Reports TODO, FIXME, XXX, and HACK markers, case-sensitive and
  matched as whole words, so "methodology" does not count but
  "TODO: fix this" does
- Prints per-tag counts, a per-file table sorted by marker count, and
  every match as file:line with the matching line, capped at `--max`
  with an honest count of what was left out
- Skips binary files and the usual noise directories: .git,
  node_modules, __pycache__, .venv, dist, and build
- Accepts `--tag` (repeatable) to report only the tags you care about

## What it deliberately does not do

- No .gitignore support: the skip list is fixed and listed above, so
  the scan is predictable; a repo with unusual generated directories
  will show them and you will see that in the report
- No comment awareness: a marker inside a string literal counts the
  same as one in a comment, because distinguishing them per language
  would make this a parser, not a tiny tool
- No dates, owners, or aging: who left the marker and when is git
  blame's job, and this tool stays one file
- No fixing: it reports unfinished work, it never edits the tree
