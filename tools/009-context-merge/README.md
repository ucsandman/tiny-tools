# 009: context-merge

A tiny script that merges multiple markdown context notes into one
deduplicated note. Agent sessions each leave their own handoff or
context note, and the next session inherits a pile of them: the same
"Decisions" section copied three times, the same "Open questions" in
two files with different answers. context-merge combines the pile:
sections are matched by their level-2 heading, identical sections
are dropped as duplicates, and sections that share a heading but
differ are kept together with a source line, so nothing is lost.

## Why it exists

Context notes compound. The first session writes a handoff note, the
second writes another, the third writes a third, and by the fourth
session the agent is reading three overlapping documents and paying
for the same paragraph three times. Deleting the older notes loses
the one paragraph that only exists in the old file; keeping them all
wastes budget on repeats. context-merge is the boring version of the
job: one command, one merged note, duplicates dropped, conflicts
kept side by side with their source named. It pairs with
handoff-note (which writes the notes) and context-tail (which trims
one note to a budget): handoff-note captures a session, context-merge
combines several sessions into one note, context-tail trims it to
fit.

## Usage

```bash
# merge two or more notes
python3 context_merge.py note-a.md note-b.md > MERGED.md

# merge every markdown file in a directory
python3 context_merge.py --dir notes/ -o MERGED.md

# keep repeated identical sections instead of dropping them
python3 context_merge.py --keep-duplicates a.md b.md

# omit the "> From <file>" lines on merged sections
python3 context_merge.py --no-source a.md b.md
```

Read-only against the input files, always. No dependencies beyond
Python 3.8+. A one-line summary goes to stderr; the merged markdown
goes to stdout (or to `--output`). Exit status is 0 on success, 1
if a file is missing or no input is given.

## What it does

- Matches sections by normalized level-2 heading text (case and
  extra whitespace ignored), keeping first-seen order
- Drops repeated sections with identical body text and counts them
  as duplicates in the footer and the stderr summary
- Keeps repeated sections with different body text under the same
  heading, with a `> From <file>` source line on each later body,
  so conflicting versions stay visible side by side
- Takes the title from the first file that has one and the preamble
  (text before the first `##` heading) from the first file that has
  one
- Uses the full given path as a source label when two input files
  share a basename, so `> From README.md` never points at two files
- Ends the merged note with a footer naming how many files were
  merged and how many duplicate sections were dropped

## What it deliberately does not do

- No semantic merging: two sections with different headings are
  never combined, even if they say the same thing in different
  words; matching is by heading text only, because judging meaning
  would make this a language model, not a tiny tool
- No reordering: sections stay in first-seen order, because the
  order the notes were written in is the order the work happened in
- No editing of the bodies: merged text is copied verbatim, so the
  output is always traceable back to its source files
- No conflict resolution: when two versions of a section disagree,
  both are kept and the human (or the next session) decides which
  one wins
