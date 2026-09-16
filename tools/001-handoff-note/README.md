# 001: handoff-note

A tiny script that turns a git repo's current state into a markdown context
note, so whoever (or whatever) picks the work up next starts with the full
picture instead of archaeology.

## Why it exists

Agent sessions end. Human sessions get interrupted. The next session always
starts with the same questions: what branch am I on, what changed, what was
left unfinished. This answers all of them in one file, in ten seconds.

## Usage

```bash
# print the note for the current repo
python3 handoff.py

# note for a different repo, saved to a file
python3 handoff.py ~/projects/my-app -o handoff.md
```

Read-only against the repo. No dependencies beyond Python 3.8+ and git.

## What it captures

- Branch, date, working tree state (staged / unstaged / untracked)
- Diff stat of the working tree vs HEAD
- Last 8 commits
- Stash entries, if any
- A "fill in before handing off" section: what I did, what's next,
  watch out for, how to verify

## What it deliberately does not do

- No full diffs (stat only; full diffs drown the note)
- No pushing, no committing, no network calls
- No opinions about your workflow
