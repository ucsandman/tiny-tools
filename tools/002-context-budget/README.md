# 002: context-budget

A tiny script that shows where your token budget goes before you spend it.
Point it at the files and directories you are about to paste into a context
window, and it reports the estimated token cost of each file, its share of
the total, and whether the whole pile fits inside your budget. Files are
sorted by cost, largest first, so the first trim target is at the top.

## Why it exists

Agent developers assemble context out of files: resume notes, transcripts,
specs, logs. The question is always the same: will this fit, and what eats
the budget. Guessing means either truncating the good stuff or discovering
mid-run that the window is full. This answers both questions in one pass.

## Usage

```bash
# measure the files you plan to paste
python3 budget.py RESUME.md docs/ transcripts/

# check against a smaller budget (default is 100000 tokens)
python3 budget.py --budget 50000 session.md

# save the markdown report to a file
python3 budget.py --budget 200000 . -o budget-report.md
```

Read-only: it never modifies inputs. No dependencies beyond Python 3.8+.

## What it does

- Walks files and directories, skips binary files (NUL-byte heuristic)
- Counts bytes, characters, and estimated tokens (4 characters per token)
- Prints a markdown table: file, tokens, chars, share of total
- Verdict: within budget or OVER BUDGET, with the amount over or spare
- Exit status 0 when within budget, 1 when over, so scripts can gate on it
- Skips `.git`, `node_modules`, `__pycache__`, and similar junk directories

## What it deliberately does not do

- No real tokenizer (tiktoken would cost a dependency and slow every run)
- No compression suggestions, no rewriting your files
- No tracking what you paste over time; one measurement per run
