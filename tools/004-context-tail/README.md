# 004: context-tail

A tiny script that trims a log or session transcript down to a token budget.
It keeps the most recent lines that fit and marks exactly what was cut, so
whoever reads the result knows the beginning is missing instead of silently
receiving a drowned context window.

## Why it exists

Agent developers paste logs and transcripts into context windows all the
time: session logs, debug output, tool-call transcripts. Those files always
grow longer than the budget, and the fix is always the same manual move:
keep the recent stuff, drop the old stuff. The manual move fails two ways.
You eyeball it and blow the budget anyway, or you trim so aggressively you
lose the error you were debugging. This does the boring version of the job:
newest lines first, a hard token cap, and a labeled cut line.

## Usage

```bash
# trim to the default budget (~20k tokens), print to stdout
python3 tail.py session-log.txt

# trim to a smaller budget
python3 tail.py --budget 5000 debug-output.txt

# trim from stdin
python3 tail.py < pasted-log.txt

# trim into a file
python3 tail.py -o trimmed.txt huge.log

# custom trim marker ({lines} and {tokens} are filled in)
python3 tail.py --budget 5000 --marker "== cut {lines} lines ==" huge.log
```

Read-only against the input unless you pass `-o`. No dependencies beyond
Python 3.8+. A one-line summary goes to stderr; the trimmed text goes to
stdout (or the `-o` file). Exit status is always 0.

## What it does

- Keeps the most recent lines that fit inside `--budget` tokens (default
  20000), estimated at 4 characters per token like context-budget
- Prepends a labeled marker when lines were cut, e.g.
  `[... trimmed 428 older line(s), ~10994 token(s), to fit a ~2000-token
  budget ...]`, so the cut is visible and countable
- Passes input through byte-identical when it already fits the budget
- Reserves a few tokens for the marker itself when trimming, so the total
  (marker plus kept lines) stays inside the budget

## What it deliberately does not do

- No mid-line truncation: if a single line exceeds the whole budget, it is
  kept whole and the summary says so
- No "smart" selection: newest lines win, always; it never tries to find
  the interesting part
- No real tokenizer (same 4-chars-per-token estimate as context-budget)
