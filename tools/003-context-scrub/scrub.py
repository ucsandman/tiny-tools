#!/usr/bin/env python3
"""context-scrub: strip secrets from text before you hand it to an agent.

Reads one or more text files (or stdin), redacts credential-like values,
and prints the cleaned text. Prints a redaction summary to stderr.

Usage:
    python3 scrub.py session-log.txt > session-log.clean.txt
    python3 scrub.py < pasted-log.txt
    python3 scrub.py -o clean.txt a.txt b.txt
"""

import argparse
import re
import sys

# Each entry: (label, compiled regex). The whole match is redacted.
PATTERNS = [
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[bprao]-[A-Za-z0-9-]{10,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe-key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "private-key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?"
            r"-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    (
        "url-credentials",
        re.compile(r"(?<=://)[^/\s:@]+:[^/\s:@]+(?=@)"),
    ),
    (
        "key-assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|api[_-]?secret|secret|password|passwd|pwd|"
            r"access[_-]?token|refresh[_-]?token|auth[_-]?token|bearer)\b"
            r"\s*[:=]\s*"
            r"(\"|')?"
            r"([A-Za-z0-9_\-./+]{8,})"
            r"(\"|')?"
        ),
    ),
]

def scrub_text(text):
    """Redact credential-like values. Returns (cleaned, {label: count})."""
    counts = {}
    for label, pattern in PATTERNS:

        def _repl(match, label=label):
            counts[label] = counts.get(label, 0) + 1
            return "[REDACTED " + label + "]"

        text = pattern.sub(_repl, text)
    return text, counts


def read_input(args):
    if not args.files:
        yield "<stdin>", sys.stdin.read()
        return
    for path in args.files:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            yield path, fh.read()


def main():
    parser = argparse.ArgumentParser(
        description="Redact secrets from text before handing it to an agent."
    )
    parser.add_argument("files", nargs="*", help="Input files (default: stdin)")
    parser.add_argument("-o", "--output", help="Write cleaned text to FILE instead of stdout")
    args = parser.parse_args()

    total_counts = {}
    chunks = []
    for _path, text in read_input(args):
        cleaned, counts = scrub_text(text)
        for label, n in counts.items():
            total_counts[label] = total_counts.get(label, 0) + n
        chunks.append(cleaned)

    out_text = "\n".join(chunks)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out_text)
    else:
        sys.stdout.write(out_text)

    total = sum(total_counts.values())
    if total:
        detail = ", ".join(
            f"{label} x{n}" for label, n in sorted(total_counts.items())
        )
        print(f"scrubbed {total} value(s): {detail}", file=sys.stderr)
    else:
        print("no credentials found", file=sys.stderr)


if __name__ == "__main__":
    main()
