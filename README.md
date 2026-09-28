# tiny-tools

One tiny free micro-tool per week, for people who build with AI agents.
Each tool is its own mini-launch. The collection compounds into a portfolio.

## The rules

1. **Tiny.** One job, done well. If it needs a config file, it is too big.
2. **Free.** MIT licensed, no accounts, no telemetry, no upsell.
3. **Real.** Every tool is run against a real input and verified before it ships.
4. **Weekly.** A new tool lands every Monday.
5. **Boring technology.** Python stdlib or shell. No dependencies unless the
   tool cannot exist without them.

## The tools

| #   | Tool | What it does |
|-----|------|--------------|
| 001 | [handoff-note](tools/001-handoff-note/) | Turns a git repo's state into a markdown context note for the next session |
| 002 | [context-budget](tools/002-context-budget/) | Shows where your token budget goes before you spend it: per-file cost report against a budget |
| 003 | [context-scrub](tools/003-context-scrub/) | Strips secrets from text before you hand it to an agent: redacts keys, tokens, and private key blocks |

## Running a tool

Each tool lives in its own directory under `tools/` with its own README.
Clone the repo, `cd` into the tool, follow its README. That is the whole
install process.
