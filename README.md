# jsf-migrator

Multi-agent **audit + fixer** framework for in-progress migrations of legacy
JSF apps toward a Spring Boot backend + Angular frontend.

It does not translate code from scratch. It assumes you already have the new
Spring + Angular stack mostly built (often manually, possibly with a rewritten
persistence layer) and helps answer the harder question: **what business logic
and UI behavior from the legacy JSF app is missing or wrong in the rewrite?**

Each agent role runs as one invocation of Google's official
[`gemini-cli`](https://github.com/google-gemini/gemini-cli) — no SDK calls, no
extra auth setup beyond what gemini-cli already needs.

## How it works

```
jsf-migrate init        # scans your three codebases, writes draft project.yaml
       │                  via a "Feature Mapper" agent
       ▼
   <you edit project.yaml, set approved: true on features to audit>
       ▼
jsf-migrate audit       # for each approved feature:
       │                  JSF Analyst → Spring Analyst → Angular Analyst → Comparator
       ▼
   specs/{jsf,spring,angular}/<feature>.json
   gaps/<feature>.md      ← human-reviewable gap report per feature
       ▼
jsf-migrate resume      # if the run stopped on a Gemini quota error
```

Phase 2 (`jsf-migrate fix`) is scaffolded but not implemented — the audit
pipeline is fully usable on its own.

## Install

In your migration project's root:

```bash
pip install git+https://github.com/<owner>/multi-agent-jsf-to-spring-angular-migration.git
```

Then make sure Google's official `gemini-cli` is on `PATH` and authenticated
(`gemini auth login` or `GEMINI_API_KEY`).

## Usage

```bash
# 1. bootstrap
jsf-migrate init --jsf ./legacy-jsf --spring ./spring-app --angular ./angular-app

# 2. open project.yaml, review the proposed features, set `approved: true`
#    on the ones you want audited

# 3. run the audit
jsf-migrate audit

# 4. read gap reports
ls migration-audit/gaps/

# at any time
jsf-migrate status
jsf-migrate resume        # picks up after quota stops
```

`--dry-run` on any command prints what gemini-cli would be invoked with,
without actually calling it.

## Customizing prompts

The bundled prompts in `src/jsf_migrator/_bundled_prompts/` are deliberately
generic. To tune them for your project, drop same-named markdown files into a
`prompts/` directory in your migration project root — the loader prefers your
override over the bundled default. See `examples/project.yaml.example` for the
full schema.

## Design doc

See [`project-spec.md`](project-spec.md) for the full design including the
state-machine contract, gemini-cli adapter rationale, and the rationale for
the pivot from "translator" to "auditor".

## Development

```bash
uv venv
uv pip install -e .[dev]
.venv/Scripts/python -m pytest -q
```

The tests mock `subprocess.run` so they don't need `gemini-cli` installed.
     