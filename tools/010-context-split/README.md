# 010: context-split

A tiny script that splits one long markdown note into numbered chunk
files, each under a token budget. A merged context note can grow
past what a single paste, a single tool call, or a single model
turn accepts. context-split cuts it into parts you can feed one
at a time: it splits at heading boundaries first and paragraph
boundaries second, so a chunk never starts or ends mid-thought
unless a single paragraph is itself bigger than the budget, in
which case it splits between words as a last resort. Joining the
chunk bodies back together reproduces the original note exactly.

## Why it exists

Merging notes solves the pile problem and trimming solves the
too-long problem, but sometimes the note is worth keeping whole
and the limit is on the other side: a chat box that caps pastes,
a tool that takes a bounded input, a model turn with a small
window. The usual answer is to cut the note by hand, which means
guessing where the token boundary falls and losing track of which
part went where. context-split is the boring version of the job:
one command, numbered part files, each under budget, each labeled
with its position, and the split points chosen at headings and
paragraphs so every chunk reads on its own. It pairs with
context-merge (which combines notes) and context-tail (which
trims one note to a budget): merge combines several sessions
into one note, split cuts one note into feedable parts, tail
trims a note down to its most recent lines.

## Usage

```bash
# split a note into chunks of at most ~4000 tokens each
python3 context_split.py session-notes.md

# smaller chunks for a tighter limit
python3 context_split.py session-notes.md --budget 1000

# read from stdin, write chunks into a directory
cat session-notes.md | python3 context_split.py --budget 1000 --out-dir parts/

# choose the filename prefix instead of the input name
python3 context_split.py session-notes.md --prefix handoff
```

Output files are named `<stem>-part-01.md`, `<stem>-part-02.md`,
and so on. Each chunk starts with an HTML comment naming its
position (`chunk 2 of 5`) and its rough token count. A one-line
summary goes to stderr. Exit status is 0 on success, 1 if the
input is missing, empty, or unreadable.

## What it does

- Splits at heading boundaries first, then at paragraph
  boundaries, then between words only when a single paragraph
  is bigger than the budget
- Never splits mid-paragraph or mid-word unless a single
  unbroken word is itself bigger than the budget
- Keeps every chunk under the budget by the same rough estimate
  context-budget uses: about one token per four characters
- Labels each chunk with its position and source, so pasted
  parts stay identifiable
- Reproduces the original note exactly when the chunk bodies
  are joined in order: nothing is added, removed, or reworded
- Reads from a file or stdin, writes only the chunk files

## What it deliberately does not do

- No tokenizing: the estimate is characters divided by four,
  which is accurate enough to size chunks and keeps the tool
  dependency free; a real tokenizer would make this a
  different tool
- No reordering or summarising: the chunks are the note, in
  order, in full, because a split that edits is a different job
- No overlap between chunks: each part stands alone, so if a
  section needs its heading for context, the heading travels
  with the section it belongs to
- No merging back: joining the bodies is a one-line `cat` of
  the part files in order, so the tool does not need a reverse
  mode
