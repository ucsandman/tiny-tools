# 003: context-scrub

A tiny script that strips secrets out of text before you hand it to an agent.
Point it at session logs, debug output, or anything you are about to paste
into a context window, and it redacts credential-like values so your
handoff note does not become a key leak.

## Why it exists

Agent developers paste a lot of context into a lot of places: resumes,
transcripts, logs, handoff notes. Those pastes routinely contain API keys,
tokens, database URLs, and private key blocks. Eyeballing is how keys leak;
this is the ten-second habit that replaces it.

## Usage

```bash
# clean a file, print to stdout
python3 scrub.py session-log.txt

# clean from stdin
python3 scrub.py < pasted-log.txt

# clean multiple files into one output
python3 scrub.py -o clean.txt a.txt b.txt
```

Read-only against the inputs unless you pass `-o`. No dependencies beyond
Python 3.8+. Prints a redaction summary to stderr.

## What it redacts

GitHub, OpenAI, Anthropic, Slack, AWS, Google, and Stripe keys, JWTs,
private key blocks (whole block, not just the header), credentials embedded
in URLs, and `key = value` style assignments for common credential names
(api_key, password, token, and friends). Every redaction is labeled, e.g.
`[REDACTED github-token]`, so you can see what class of secret was there.

## What it deliberately does not do

- No intent analysis: a value that looks like a key is redacted even if it
  is a placeholder; check the stderr summary to see what was caught
- No restoration: the redaction is one-way, by design
- No network calls, no storage, no telemetry
