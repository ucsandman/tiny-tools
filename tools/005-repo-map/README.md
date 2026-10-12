# 005: repo-map

A tiny script that turns an unfamiliar codebase into a one-page markdown
map: totals, a depth-limited directory tree, the biggest files by line
count, and the entry points it can detect. Run it at the start of a
session and paste the output to the agent, so it can orient itself
without spending the first ten minutes listing directories by hand.

## Why it exists

The most expensive part of starting an agent on an unfamiliar repo is
orientation: the agent burns turns and tokens wandering the directory
tree, reading the wrong files first, asking where the entry point is.
Humans do the same thing in their heads the first time they open a new
codebase. A one-page map answers the three questions that matter up
front: how big is this thing, what is the shape of it, and where do I
start. It costs one run and reads like a note, not a dump.

## Usage

```bash
# map the current directory, print markdown to stdout
python3 repo_map.py

# map another repo
python3 repo_map.py /path/to/repo

# deeper tree
python3 repo_map.py --depth 5 repo

# more "biggest files"
python3 repo_map.py --top 20 repo

# also skip a directory
python3 repo_map.py --exclude docs --exclude tests repo

# save the map
python3 repo_map.py repo > MAP.md
```

Read-only against the scanned directory, always. No dependencies beyond
Python 3.8+. A one-line summary goes to stderr; the markdown goes to
stdout. Exit status is 0 on success, 1 if the path is not a directory.

## What it does

- Prints totals: directories, text vs binary files, lines, size, and a
  rough whole-repo token estimate (4 chars per token, same as
  context-budget), so you know whether the repo fits in context at all
- Prints a directory tree limited by `--depth` (default 3), skipping
  noise directories: `.git`, `node_modules`, `__pycache__`, virtual
  envs, build outputs, IDE folders, and more
- Lists the biggest files by line count (`--top`, default 10) with a
  per-file rough token estimate, so the agent knows which files are
  worth reading first and which are cheap to skim
- Detects entry points: READMEs, license files, `main.*` / `index.*` /
  `__main__.py`, package configs (`package.json`, `pyproject.toml`,
  `go.mod`, `Cargo.toml`), `npm run` scripts, `[project.scripts]`
  console scripts, and `Makefile` targets

## What it deliberately does not do

- No dependency analysis: it does not parse imports or build a call
  graph; knowing what calls what is a real tool, not a tiny one
- No git history: branch state and recent changes are handoff-note's
  job, not this one's
- No content summarization: it tells you where things are, not what
  they mean; the agent still has to read the files
- No real tokenizer (same 4-chars-per-token estimate as the other
  context tools)
