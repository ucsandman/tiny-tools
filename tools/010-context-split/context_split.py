#!/usr/bin/env python3
"""context-split: split one long markdown note into numbered chunks.

Usage:
    python3 context_split.py NOTE.md [--budget N] [--out-dir DIR]
    cat NOTE.md | python3 context_split.py [--budget N]

A merged context note can grow past what a single paste, a single
tool call, or a single model turn accepts. context-split cuts it
into numbered part files, each under a token budget, splitting at
heading boundaries first and paragraph boundaries second, so a
chunk never starts or ends mid-thought unless a single paragraph
is itself bigger than the budget.

Token counts use the same rough estimate as context-budget:
about one token per four characters. That is accurate enough to
size chunks; it is not a tokenizer.

Output files are named <stem>-part-01.md, <stem>-part-02.md, and
so on, in the current directory (or --out-dir). Each chunk starts
with an HTML comment naming its position, so the parts stay
identifiable when pasted separately. A one-line summary goes to
stderr. Exit status is 0 on success, 1 if the input is missing
or unreadable.
"""

import argparse
import os
import re
import sys

CHARS_PER_TOKEN = 4
HEADING_RE = re.compile(r"^#{1,6}\s")


def estimate_tokens(text):
    return len(text) // CHARS_PER_TOKEN


def split_paragraphs(text):
    """Split text into blank-line-separated blocks, keeping the
    blank lines attached to the block that follows them."""
    blocks = []
    current = []
    for line in text.splitlines(keepends=True):
        if line.strip() == "" and current:
            current.append(line)
            blocks.append("".join(current))
            current = []
        else:
            current.append(line)
    if current:
        blocks.append("".join(current))
    return [b for b in blocks if b.strip() != ""]


def split_sections(text):
    """Split markdown into sections at heading lines. Text before
    the first heading is its own leading section."""
    sections = []
    current = []
    for line in text.splitlines(keepends=True):
        if HEADING_RE.match(line) and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))
    return [s for s in sections if s.strip() != ""]


def split_long_block(block, budget_tokens):
    """Split one oversized block by lines, only used when a single
    paragraph is bigger than the budget. A single line longer than
    the budget is split between whitespace-separated tokens, keeping
    every separator, so joining the pieces reproduces the block
    exactly. Accounting is by characters, so rounding never lets a
    piece creep over budget. A single token longer than the budget
    (one unbroken word) is the only case that can exceed it."""
    pieces = []
    current = []
    current_chars = 0

    def flush_current():
        nonlocal current, current_chars
        if current:
            pieces.append("".join(current))
            current = []
            current_chars = 0

    for line in block.splitlines(keepends=True):
        if (current_chars + len(line)) // CHARS_PER_TOKEN > budget_tokens:
            flush_current()
        if estimate_tokens(line) <= budget_tokens:
            current.append(line)
            current_chars += len(line)
            continue
        # Overlong line: split between tokens, separators included.
        for token in re.findall(r"\S+\s*|\s+", line):
            if current and (current_chars + len(token)) // CHARS_PER_TOKEN > budget_tokens:
                flush_current()
            current.append(token)
            current_chars += len(token)
    flush_current()
    return pieces


def split_text(text, budget_tokens):
    """Split text into chunks, each at most budget_tokens by the
    rough estimate. Split at section boundaries, then at paragraph
    boundaries, then at line boundaries as a last resort."""
    chunks = []
    current = []
    current_chars = 0

    def flush():
        nonlocal current, current_chars
        if current:
            chunks.append("".join(current))
            current = []
            current_chars = 0

    def fits(unit):
        return (current_chars + len(unit)) // CHARS_PER_TOKEN <= budget_tokens

    def add(unit):
        nonlocal current_chars
        current.append(unit)
        current_chars += len(unit)

    for section in split_sections(text):
        if fits(section):
            add(section)
            continue
        flush()
        if estimate_tokens(section) <= budget_tokens:
            add(section)
            continue
        for paragraph in split_paragraphs(section):
            if fits(paragraph):
                add(paragraph)
                continue
            flush()
            if estimate_tokens(paragraph) <= budget_tokens:
                add(paragraph)
                continue
            for piece in split_long_block(paragraph, budget_tokens):
                if not fits(piece):
                    flush()
                add(piece)
    flush()
    return chunks


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Split a markdown note into numbered chunks under "
                    "a token budget.")
    parser.add_argument("input", nargs="?",
                        help="markdown file to split (reads stdin if omitted)")
    parser.add_argument("--budget", type=int, default=4000,
                        help="max estimated tokens per chunk (default: 4000)")
    parser.add_argument("--out-dir", default=".",
                        help="directory to write chunk files into "
                             "(default: current directory)")
    parser.add_argument("--prefix",
                        help="filename prefix for chunks "
                             "(default: input filename without extension)")
    args = parser.parse_args(argv)

    if args.budget < 1:
        print("error: --budget must be at least 1", file=sys.stderr)
        return 1

    if args.input:
        try:
            with open(args.input, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            print("error: cannot read %s: %s" % (args.input, exc),
                  file=sys.stderr)
            return 1
        stem = args.prefix or os.path.splitext(
            os.path.basename(args.input))[0]
    else:
        text = sys.stdin.read()
        if not text.strip():
            print("error: no input given (file or stdin)", file=sys.stderr)
            return 1
        stem = args.prefix or "note"

    if not text.strip():
        print("error: input is empty", file=sys.stderr)
        return 1

    chunks = split_text(text, args.budget)
    total_tokens = estimate_tokens(text)

    try:
        os.makedirs(args.out_dir, exist_ok=True)
    except OSError as exc:
        print("error: cannot create %s: %s" % (args.out_dir, exc),
              file=sys.stderr)
        return 1

    paths = []
    for index, chunk in enumerate(chunks, start=1):
        name = "%s-part-%02d.md" % (stem, index)
        path = os.path.join(args.out_dir, name)
        header = ("<!-- chunk %d of %d, split from %s, "
                  "~%d tokens -->\n\n"
                  % (index, len(chunks),
                     args.input if args.input else "stdin",
                     estimate_tokens(chunk)))
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(header + chunk)
        except OSError as exc:
            print("error: cannot write %s: %s" % (path, exc),
                  file=sys.stderr)
            return 1
        paths.append(path)

    print("split ~%d tokens into %d chunk(s) of at most ~%d tokens: %s"
          % (total_tokens, len(chunks), args.budget,
             ", ".join(paths)),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
