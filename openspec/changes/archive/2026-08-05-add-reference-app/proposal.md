## Why

The examples demonstrate mechanics but not a system: four toy apps with no
domain, no interaction between namespaces, no async lifecycle, and — the
real gap — nothing in CI ever boots them, so they can silently rot against
the kernel. A reference application is the demand-validation instrument for
the whole project: building and continuously testing a realistic modular
monolith on the kernel surfaces the API frictions no unit test can, and
gives every evaluator the worked answer to "what does a real SPOC project
look like".

## What Changes

- The example project becomes a coherent domain — a small storefront
  monolith: `catalog` (products), `orders` (references catalog across
  namespaces at runtime, through the registry), and `accounts` — plus the
  existing plugin surface.
- Both lifecycles are demonstrated: the existing synchronous entry point,
  and an asynchronous entry point whose declaration carries coroutine
  hooks and is booted with `astart`.
- The HTTP projection stays and becomes the domain's API: routes are still
  derived purely by enumerating the registry.
- The suite gains an examples test module that boots the example project
  through the public API and exercises: registry contents, cross-namespace
  resolution, the plugin registrations, the route projection, and both
  entry paths. CI installs the examples dependency group so the FastAPI
  projection is genuinely constructed, not skipped.
- The toy apps (`demo`, `other`, `another`) are deleted — the domain apps
  replace them (greenfield; the history is the history).

## Capabilities

### New Capabilities

- `reference-application`: the repository carries one runnable reference
  project that exercises the kernel's public contracts — multiple apps
  across modes, cross-namespace resolution, plugins, both lifecycles, and a
  registry-projected surface — and the test suite boots it, so drift
  between the kernel and its worked example fails CI.

### Modified Capabilities

<!-- none — kernel behavior is untouched -->

## Impact

- Changed code: `examples/` (apps reshaped, async entry added),
  `tests/test_examples.py` (new), CI workflow (examples group installed).
- Dependencies: none published; FastAPI stays in the `examples` dev group.
- Docs: examples docs page updated to the domain; README quick-start
  unchanged.
