# 008: env-check

A tiny script that finds the environment variables a codebase expects:
shell `$VAR` and `${VAR}`, Python `os.environ` and `os.getenv`, and
JavaScript `process.env`. It reports each variable as set or unset
against the current environment, with any default found in the code
and the files that reference it. Run it at the start of a session in
an unfamiliar repo to see what the code needs before you run it.

## Why it exists

Every project with external services has a hidden setup step: the
environment variables it expects, scattered across scripts, app code,
and deploy configs. The README usually says "set your env vars" and
never says which ones. Grep finds the references, but grep gives you
raw lines with no shape: no set-versus-unset verdict, no defaults,
nothing you can paste into a session note. env-check is the boring
version of the job: one command, one table, every variable located
and checked against the shell you are standing in. It pairs with
repo-map (the shape of the codebase) and handoff-note (where the last
session stopped): repo-map says what exists, env-check says what the
code needs from its environment.

## Usage

```bash
# scan the current directory
python3 env_check.py

# scan another directory
python3 env_check.py /path/to/repo

# only the variables missing from this environment
python3 env_check.py --unset-only repo

# save it or pipe it onward
python3 env_check.py repo > ENV-NEEDED.md
```

Read-only against the scanned tree, always. No dependencies beyond
Python 3.8+. A one-line summary goes to stderr; the markdown goes to
stdout. Exit status is 0 on success, 1 if the path is not a directory.

## What it does

- Reports shell `$VAR` and `${VAR}` (including `:-default`,
  `-default`, and `:?message` forms), Python `os.environ["VAR"]`,
  `os.environ.get("VAR", default)`, and `os.getenv("VAR", default)`,
  and JavaScript `process.env.VAR` and `process.env["VAR"]`
- Marks each variable set or UNSET against the current environment,
  so the same report answers "what does this code need" and "what is
  missing here"
- Shows defaults found in the code, so you can tell a variable with
  a sane fallback from one that will crash without a value
- Lists every file that references each variable
- Skips binary files and the usual noise directories: .git,
  node_modules, __pycache__, .venv, dist, and build

## What it deliberately does not do

- No .env file parsing: a `.env` file assigns variables, it does not
  reference them, so it adds nothing to the report; the current
  environment is the source of truth for what is set
- No comment or string awareness: a reference inside a comment counts
  the same as one in code, because distinguishing them per language
  would make this a parser, not a tiny tool
- No values shown: the report names variables and their defaults from
  the code, never the values set in your environment, so it is safe
  to paste into a session note or a ticket
- No fixing: it reports what is missing, it never writes a .env file
  or exports anything into your shell
