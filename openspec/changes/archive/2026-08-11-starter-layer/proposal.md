# Starter Layer

## Why

The kernel is finished and validated — registry, kinds, lifecycle, diagnostics — but the
layer where developers actually live is empty. A gap analysis against Django, Spring Boot,
Flask, FastAPI, and Sanic, cross-checked against the plugin-architecture literature
(Eclipse extension points, OSGi's 20-year retrospective, platform-ecosystem research),
converged on one finding: SPOC lacks not capabilities but **boundary resources** — a
conventional kind vocabulary, starter templates that generate a working surface, and the
recipes that connect them. Without a shared vocabulary no reusable app ecosystem can form;
without a starter, `spoc init` produces a project that prints its registry and exits.

One genuine defect rides along: `spoc.toml` tables outside `[spoc]` are parsed, validated
by nothing, and silently discarded — in a project whose stated contract is that a typo
never boots a half-working project.

## What Changes

- **Bless a conventional kind vocabulary.** A documented default set of kinds — what each
  means, which lifecycle hooks each uses, and the resource-lifecycle convention (a
  `resources` kind whose components are opened by kind startup hooks, reached via
  `resolve`, and closed by kind shutdown hooks). Deviation stays allowed; the default
  becomes the convention the docs teach, the scaffolder emits, and the ecosystem targets.
- **Ship a starter template set.** A second built-in template set that generates a
  *runnable application*: a transport-neutral projection module and a project-owned
  command surface, both derived from the registry, plus the vocabulary wired end to
  end. The generated project needs no third-party dependency; binding the projection to
  a transport (HTTP, messaging, workers) ships as short runnable documentation recipes,
  not generated code. Template sets are inert data — this is a data change bounded by
  the existing scaffold-templates contract.
- **Stop discarding app-owned configuration.** Top-level tables in `spoc.toml` outside the
  kernel's own table become reachable by the application through the framework's exposed
  configuration instead of vanishing. The kernel's own table stays a closed key set;
  validation of app-owned tables stays the app's job, through a documented
  settings-validation seam.
- **Demonstrate the vocabulary in the reference application.** The storefront example
  exercises the resource-lifecycle convention so the recipe is executable, not prose.
- **Record kind-contribution as deliberately deferred.** Third-party packages declaring
  their own kinds (Eclipse-style, namespaced by contributor) is written down in the
  design as a known-good future shape with its constraints — and explicitly not built.

## Capabilities

### New Capabilities

- `kind-vocabulary`: the conventional default vocabulary — which kinds exist by default,
  what each means, the resource-lifecycle convention, and the requirement that the default
  generation and the documentation agree with it.
- `starter-templates`: the shipped starter template set — what a generated starter project
  must contain, that it runs unedited without third-party dependencies, and that its
  surfaces are projections of the registry. The starter is transport-neutral; the
  build-vs-adopt decision is recorded in the design.

### Modified Capabilities

- `project-configuration`: app-owned top-level tables are exposed to the application
  rather than silently discarded; the kernel's own table remains a closed key set. The
  documented settings-validation seam stays tool-agnostic; its worked-example choice is
  recorded in the design.
- `reference-application`: the storefront demonstrates the resource-lifecycle convention
  (a resource opened at startup, resolved by an app, closed at shutdown).

## Impact

- **Code:** `src/spoc/core/config.py` and the `Config` record in `src/spoc/framework.py`
  (app-owned tables); `src/spoc/scaffold/templates/` (new starter set — data only);
  `examples/` (resource demonstration). No kernel registry/loader/identity changes.
- **Docs:** new Learn material for the vocabulary and the resource recipe; starter
  walkthrough; configuration page gains the app-owned-tables contract. Docs snippets must
  run (project policy).
- **Surface:** the starter template set becomes a new `template-set:*` entry in
  `[tool.spoc.stability]`; `apicheck` baseline gains it. New public docs pages. No
  importable-name changes expected.
- **Tests:** generate-and-boot test for the starter set (pattern exists for `default`);
  config passthrough tests; example tests extend.
- **Explicitly out of scope:** kind contribution by installed packages (deferred design
  note); a `spoc run` command in SPOC's own CLI (the generated project owns its command
  surface — the kernel never executes); typed config binding in the kernel (ecosystem
  tooling adopted via the documented seam instead).
