#!/usr/bin/env python3
"""Merge multiple markdown context notes into one deduplicated note.

Agent sessions each leave their own handoff or context note, and the
next session inherits a pile of them: the same "Decisions" section
copied three times, the same "Open questions" in two files with
different answers. context-merge combines the pile into one note:
sections are matched by their level-2 heading, identical sections
are dropped as duplicates, and sections that share a heading but
differ are kept together with a source line so nothing is lost.

Usage:
    python3 context_merge.py note1.md note2.md > MERGED.md
    python3 context_merge.py --dir notes/ -o MERGED.md
    python3 context_merge.py --keep-duplicates a.md b.md

Rules:
  * The title (# heading) comes from the first file that has one.
  * Content before the first ## heading is the preamble; only the
    first file's preamble is kept.
  * Sections are matched by normalized heading text (case and extra
    whitespace ignored). First occurrence sets the position.
  * A repeated section with identical body text is dropped and
    counted as a duplicate.
  * A repeated section with different body text is appended under
    the same heading with a "> From <file>" source line.
  * A summary goes to stderr; the merged markdown goes to stdout
    (or to --output). Exit status is 0 on success, 1 on bad input.

Only Python 3.8+ stdlib. Read-only against the input files.
"""

import argparse
import os
import re
import sys

HEADING_RE = re.compile(r"^##\s+(.*)$")
TITLE_RE = re.compile(r"^#\s+(.*)$")


def normalize_heading(text):
    return " ".join(text.strip().casefold().split())


def normalize_body(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def parse_note(path):
    """Split a markdown file into (title, preamble, [(heading, body)])."""
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    title = None
    preamble_lines = []
    sections = []
    current_heading = None
    current_body = []

    for line in lines:
        title_match = TITLE_RE.match(line)
        if title_match and title is None and current_heading is None \
                and not sections and not preamble_lines:
            title = title_match.group(1).strip()
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match:
            if current_heading is not None:
                sections.append((current_heading, "\n".join(current_body)))
            current_heading = heading_match.group(1).strip()
            current_body = []
        elif current_heading is None:
            preamble_lines.append(line)
        else:
            current_body.append(line)

    if current_heading is not None:
        sections.append((current_heading, "\n".join(current_body)))

    return title, "\n".join(preamble_lines).strip(), sections


def merge_notes(paths, keep_duplicates=False, no_source=False):
    """Merge parsed notes. Returns (markdown, files, sections, duplicates)."""
    title = None
    preamble = None
    order = []          # normalized headings, in first-seen order
    merged = {}         # normalized heading -> {"heading": str, "bodies": []}
    duplicates = 0
    files_read = 0

    basenames = {}
    for path in paths:
        basenames[os.path.basename(path)] = basenames.get(
            os.path.basename(path), 0) + 1

    for path in paths:
        # Same-named files from different directories get the full path
        # as their source label, so "> From README.md" stays unambiguous.
        if basenames[os.path.basename(path)] > 1:
            name = path
        else:
            name = os.path.basename(path)
        note_title, note_preamble, sections = parse_note(path)
        files_read += 1
        if title is None and note_title:
            title = note_title
        if preamble is None and note_preamble:
            preamble = note_preamble

        for heading, body in sections:
            key = normalize_heading(heading)
            body_norm = normalize_body(body)
            if key not in merged:
                merged[key] = {"heading": heading, "bodies": [(name, body)]}
                order.append(key)
                continue
            seen_bodies = [normalize_body(b) for _, b in merged[key]["bodies"]]
            if body_norm in seen_bodies:
                if not keep_duplicates:
                    duplicates += 1
                    continue
            merged[key]["bodies"].append((name, body))

    out = []
    out.append("# " + (title or "Merged context note"))
    out.append("")
    if preamble:
        out.append(preamble)
        out.append("")

    for key in order:
        entry = merged[key]
        out.append("## " + entry["heading"])
        out.append("")
        for index, (source, body) in enumerate(entry["bodies"]):
            if index > 0 and not no_source:
                out.append("> From " + source)
                out.append("")
            out.append(body.strip())
            out.append("")
        # strip the trailing blank added after the last body
        while out and out[-1] == "":
            out.pop()
        out.append("")

    while out and out[-1] == "":
        out.pop()
    out.append("")
    out.append("---")
    out.append("")
    footer = "Merged from %d file%s." % (
        files_read, "" if files_read == 1 else "s")
    if duplicates:
        footer += " %d duplicate section%s dropped." % (
            duplicates, "" if duplicates == 1 else "s")
    out.append(footer)
    out.append("")

    return "\n".join(out), files_read, len(order), duplicates


def collect_paths(args):
    paths = list(args.files)
    if args.dir:
        if not os.path.isdir(args.dir):
            print("error: not a directory: %s" % args.dir, file=sys.stderr)
            sys.exit(1)
        found = sorted(
            os.path.join(args.dir, name)
            for name in os.listdir(args.dir)
            if name.endswith(".md")
            and os.path.isfile(os.path.join(args.dir, name))
        )
        paths.extend(found)
    if not paths:
        print("error: no input files given", file=sys.stderr)
        sys.exit(1)
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print("error: file not found: %s" % ", ".join(missing), file=sys.stderr)
        sys.exit(1)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Merge markdown context notes into one deduplicated note.")
    parser.add_argument("files", nargs="*", help="markdown notes to merge")
    parser.add_argument("--dir", metavar="DIR",
                        help="merge every .md file in this directory")
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="keep repeated identical sections instead of "
                             "dropping them")
    parser.add_argument("--no-source", action="store_true",
                        help="omit the '> From <file>' lines on merged "
                             "sections")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write the merged note to FILE instead of stdout")
    args = parser.parse_args(argv)

    paths = collect_paths(args)
    markdown, files_read, section_count, duplicates = merge_notes(
        paths,
        keep_duplicates=args.keep_duplicates,
        no_source=args.no_source,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    else:
        sys.stdout.write(markdown)

    summary = "Merged %d file%s into %d section%s" % (
        files_read, "" if files_read == 1 else "s",
        section_count, "" if section_count == 1 else "s")
    if duplicates:
        summary += ", %d duplicate%s dropped" % (
            duplicates, "" if duplicates == 1 else "s")
    print(summary + ".", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
