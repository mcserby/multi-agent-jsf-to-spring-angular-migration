# jsf-migrator — project spec

A multi-agent **audit + fixer** framework that helps validate and complete an in-progress migration of a legacy JSF application toward a Spring Boot backend + Angular frontend.

Originally scoped as a from-scratch translator; pivoted to a **three-way auditor** because the consuming project already has a manually-built Spring Boot app (with rewritten JPA/Postgres persistence) and an Angular frontend, and the real question is *what business logic and UI behavior from the legacy JSF app is missing or wrong in the new stack*.

---

## Phases

1. **Audit (phase 1, default)** — read-only. Analyze each codebase, propose feature mappings, compare, produce gap reports. Never writes code.
2. **Fix (phase 2, opt-in, later)** — given an approved gap report for a specific feature, apply targeted patches to the Spring or Angular code.

Phase 1 is built first and fully usable on its own; phase 2 is stubbed.

---

## Agents

| Role               | Reads                                          | Writes                                |
|--------------------|------------------------------------------------|---------------------------------------|
| Feature Mapper     | source trees of all three codebases            | draft `project.yaml` feature mappings |
| JSF Analyst        | JSF pages + managed beans for a feature        | `specs/jsf/<feature>.json`            |
| Spring Analyst     | Spring controllers + services for a feature    | `specs/spring/<feature>.json`         |
| Angular Analyst    | Angular components + services for a feature    | `specs/angular/<feature>.json`        |
| Comparator         | the three specs for a feature                  | `gaps/<feature>.md`                   |
| Spring Fixer*      | a gap report                                   | patches in the Spring tree            |
| Angular Fixer*     | a gap report                                   | patches in the Angular tree           |

`*` Phase 2 only.

---

## LLM backend

**Google `gemini-cli` (official, ~v0.42)** invoked as a subprocess per agent step. The orchestrator does *not* use the Vertex AI SDK directly — auth, file I/O, and tool calls all happen inside gemini-cli.

- Each agent step = one `gemini -p "<prompt>" --yolo -m <model>` invocation (exact flags abstracted in `gemini_adapter.py` so v0.42 specifics can be tweaked in one place).
- Prompts are passed via stdin when long, via `-p` when short.
- Model id is set in `project.yaml` (e.g. `gemini-2.5-pro-preview-...`).

### Token budget

The original spec called for "agents periodically check stats." With gemini-cli the realistic safety net is **failure detection**: when a gemini invocation exits non-zero with a quota/rate-limit pattern in stderr, the orchestrator marks the current task as `interrupted`, persists state, and exits cleanly. `jsf-migrate resume` picks up where it left off.

Quota patterns matched (case-insensitive): `quota`, `rate limit`, `RESOURCE_EXHAUSTED`, `429`, `exceeded`. Configurable in `project.yaml`.

---

## Workflow

```
1. jsf-migrate init
     ↓ scans jsf/spring/angular roots
     ↓ runs Feature Mapper agent
   draft project.yaml + state.json

2. <human edits project.yaml>  ← approve/correct feature mappings

3. jsf-migrate audit
     ↓ for each feature:
     ↓   JSF Analyst → Spring Analyst → Angular Analyst → Comparator
   specs/ + gaps/<feature>.md

4. <human reviews gaps/*.md>

5. (later) jsf-migrate fix --feature <id>
```

If the run is interrupted by quota:
```
6. jsf-migrate resume
```

`jsf-migrate status` shows what's done/pending/interrupted.

---

## Configuration

**`project.yaml`** lives in the consuming migration project's root. Schema (pydantic-validated):

```yaml
version: 1

source:
  jsf:
    path: ./legacy-jsf
    framework_version: "JSF 2.3"
    bean_style: CDI            # or ManagedBean
  spring:
    path: ./spring-app
    java_version: 21
    package_root: com.example.myapp
  angular:
    path: ./angular-app
    version: 17
    component_style: standalone

gemini:
  model: gemini-2.5-pro-preview-...   # exact id at runtime
  yolo: true
  extra_args: []                       # passed verbatim to gemini-cli
  quota_patterns:                      # additional stderr patterns -> graceful stop
    - "RESOURCE_EXHAUSTED"

paths:
  prompts: ./prompts                   # optional override dir; falls back to bundled defaults
  output: ./migration-audit            # specs/ and gaps/ live here

features:
  - id: user-management
    description: "User CRUD + auth"
    jsf:
      pages:   ["src/main/webapp/users/*.xhtml"]
      beans:   ["src/main/java/.../UserBean.java"]
    spring:
      controllers: ["src/main/java/.../UserController.java"]
      services:    ["src/main/java/.../UserService.java"]
    angular:
      components: ["src/app/users/"]
      services:   ["src/app/users/user.service.ts"]
```

The `features` list is **auto-proposed** by `jsf-migrate init`; the human approves/edits before `audit`.

---

## State

**`state.json`** in the migration project's root. Single source of truth for progress.

```json
{
  "version": 1,
  "phase": "audit",
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "interrupted_reason": null,
  "features": {
    "user-management": {
      "status": "audited",
      "tasks": {
        "jsf_analysis":     { "status": "completed", "output": "specs/jsf/user-management.json" },
        "spring_analysis":  { "status": "completed", "output": "specs/spring/user-management.json" },
        "angular_analysis": { "status": "completed", "output": "specs/angular/user-management.json" },
        "comparison":       { "status": "completed", "output": "gaps/user-management.md" }
      }
    }
  }
}
```

Statuses: `pending | in_progress | completed | failed | interrupted`.

---

## Distribution

Installable Python package. The consuming migration project does:

```bash
pip install git+https://github.com/mcserby/multi-agent-jsf-to-spring-angular-migration.git
```

Then in the migration project root:

```bash
jsf-migrate init
# edit project.yaml
jsf-migrate audit
```

Prompts can be overridden by dropping same-named markdown files into `<migration-project>/prompts/`. The loader searches the override dir first, then falls back to bundled defaults.

---

## Repo layout (this repo)

```
src/jsf_migrator/
  cli.py                  # entry: init / audit / fix / status / resume
  orchestrator.py         # state machine
  config.py               # project.yaml schema
  state.py                # state.json read/write
  gemini_adapter.py       # subprocess wrapper, quota detection
  prompts.py              # template loader (project override → bundled)
  planner.py              # source-tree scan
  alignment.py            # auto-propose feature mappings
  budget.py               # graceful-stop logic
  agents/
    base.py
    jsf_analyst.py
    spring_analyst.py
    angular_analyst.py
    comparator.py
    spring_fixer.py       # stub (phase 2)
    angular_fixer.py      # stub (phase 2)
  _bundled_prompts/       # default prompts shipped inside the wheel
tests/                    # unit tests; subprocess mocked
examples/                 # project.yaml.example
```

---

## Open items

- Exact gemini-cli flag set for v0.42 — verify on first real run, tweak `gemini_adapter.py` in one place if needed.
- Exact Gemini model id (Pro 3.1 Preview) — supplied by the migration project's `project.yaml`.
- Spring/Angular fixer agents — designed but not implemented in phase 1.
