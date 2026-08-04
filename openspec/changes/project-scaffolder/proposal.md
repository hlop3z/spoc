## Why

Declaring a framework now costs five lines, but *assembling a project* still costs six
coordinated files across four directories — `config/spoc.toml`, `framework/framework.py`,
`apps/<app>/{__init__,models,views}.py`, and an entry point — whose contents must agree with
each other. The kind names passed to `Framework(...)` must match the module names inside every
app package; the app names in `spoc.toml` must match the directories on disk; the mode cascade
must be understood before the first app is added. Nothing checks any of that until `start()`
runs, and the errors — precise as they are — arrive only after the whole skeleton has been
assembled by hand.

The `framework-object-api` change collapsed the declaration and explicitly parked this: "a CLI
/ project scaffolder — attractive later, out of scope here." The downstream evidence that
"later" has arrived is that zmag declares a `zmag-init` entry point whose module does not
exist — an author reached for a scaffolder, found none, and shipped a broken entry point
rather than write one. Project assembly is now the largest remaining cost in the kernel's
developer experience, and the only part of it a new user meets first.

## What Changes

- A **scaffolding capability** that emits a complete, runnable project from a single command:
  the configuration file, the framework declaration, one starter app, and an entry point that
  starts successfully with zero edits.
- A second, more frequently used operation: **adding an app** to an existing project —
  creating the package with a module per declared kind and registering it in the correct mode
  list, so the two stay in agreement by construction rather than by discipline.
- **Generation is refusal-safe**: an operation that would overwrite existing user content
  fails and names the conflict instead of clobbering it.
- The **project shape being emitted is treated as data**, not as strings embedded in code, so
  a downstream framework built on spoc can supply its own shape and get an `init` command for
  free instead of hand-writing one. This is what makes zmag's missing `zmag-init` a solved
  problem rather than a duplicated one.
- **The zero-runtime-dependency invariant is preserved.** `dependencies = []` is a stated
  guarantee of the published package; installing the kernel MUST NOT acquire anything the
  scaffolder needs. The scaffolder is therefore an opt-in surface, and the invariant is a
  requirement of this change rather than a caveat to it.

## Capabilities

### New Capabilities

- `project-scaffolding`: generating a runnable project skeleton and adding apps to an existing
  project — what is emitted, what makes the result valid, and how conflicts with existing
  files are refused rather than resolved.
- `scaffold-templates`: the emitted project shape as a declared, replaceable data set, and the
  contract a downstream framework satisfies to supply its own.

### Modified Capabilities

None. The kernel's observable behavior is unchanged — a scaffolded project is one a user could
have typed by hand, and nothing in discovery, configuration, identity, or resolution moves.
That the change is purely additive is the point: if scaffolding required a kernel change, the
project layout would be under-specified.

## Impact

- **Critical concerns requiring a build-vs-adopt decision before implementation** (deferred to
  `/ai:decide`, tool choices deliberately not made here):
  - *Template rendering and project generation* — mature, widely used scaffolding tools exist
    for exactly this problem, and the canon's rebuild-cost precedent applies directly.
  - *Command-line surface* — argument parsing, subcommands, and help output.
  - *Filesystem write safety* — refusing to clobber, partial-write behavior on failure, and
    path traversal in user-supplied names. Correctness-sensitive: it writes to a user's disk.
- **Distribution**: a new opt-in install surface and a console entry point. `dependencies = []`
  in `pyproject.toml` stays literally unchanged; whatever the scaffolder needs is acquired only
  by users who ask for it.
- **Kernel**: no change to `src/spoc/` behavior. The scaffolder consumes the same conventions
  the kernel already documents; it does not become a second definition of them.
- **Docs**: the getting-started path currently walks through hand-assembly and would lead with
  the generated project instead.
- **Downstream**: zmag can delete its broken `zmag-init` declaration and supply a template set.
