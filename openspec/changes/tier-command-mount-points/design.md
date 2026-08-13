## Context

Four packages each ship a command-line adapter exposing one function of the same shape:

| Package            | Mount                          | Commands                  | Injection            |
| ------------------ | ------------------------------ | ------------------------- | -------------------- |
| `spoc.scaffold`    | `cli.register`                 | `init`, `app`             | kinds, template source |
| `spoc.diagnostics` | `cli.register`                 | `check`, `list`, `explain` | none                 |
| `spoc.projection`  | `cli.register`                 | `projection`              | none                 |
| `spoc.stubs`       | `cli.register`                 | `stubs`                   | none                 |

Each declares `__all__ = ["register"]` in its `cli` module, and none is re-exported from its
package's `__init__`. The tier derivation reads a package's published namespace, so all four
resolve to `internal` — they carry no promise and may vanish in a patch.

`spoc.cli` is the composition root that mounts all four; it is also the only caller. The
mechanism is nonetheless deliberate: `scaffold.cli.register` takes `derive_kinds` and
`source_factory` precisely so a composition root other than SPOC's own can supply them, and
`docs/docs/how-to/ship-a-framework.md` documents mounting as the way a downstream framework
publishes the generation line under its own name.

The surrounding contract is already public — `ENTRY_POINT_GROUP` is exported and
`template-set:default` is listed public — so a framework author is promised the template path
and not the command path. `DECISIONS.md` recorded this as an open question scoped to the
scaffolder alone. Inspection during this change found the other three mount points are
structurally identical, which is what widened it.

## Goals / Non-Goals

**Goals:**

- Every mount point carries a stated tier, so no part of the downstream path is silent.
- The tier states what would settle it, so the openness is deliberate rather than unexamined.
- The spec gains the general rule, so the next half-promised path is a defect the contract
  names rather than a question someone happens to notice.
- The shipped `spoc` program keeps using the same mounts, so the extension point cannot rot
  untested.

**Non-Goals:**

- Changing any signature, including replacing the parser type. Deliberately excluded — see
  the decision below.
- Changing any command's behavior, arguments, or output.
- Promoting anything to `public`. That question is what `provisional` defers.
- Building a mount registry, a plugin protocol, or a command-description format. The mount is
  a function call and stays one.

## Decisions

### Tier all four at `provisional`, not the scaffolder alone

`DECISIONS.md` framed the question around `scaffold.cli.register` because that is where the
public half of the path lives. Restricting the promotion there would still leave three
identical siblings internal, and a framework author reading the how-to would find `hello init`
promised and `hello check` not — the same defect one level down.

The Django-admin analogy the how-to already draws settles it: `django-admin` is `startproject`
*and* `check`. A downstream framework that can scaffold but cannot validate has half a CLI, so
the generation and inspection groups belong to one path and take one decision. Rule 7 —
coherence beats minimal diff.

*Alternative rejected*: scaffolder only, revisit the rest later. It re-opens as the identical
question with the identical answer, having meanwhile shipped an inconsistency.

### `provisional`, not `public`

The signature takes the parsing library's own private subparser type. Promising it in
perpetuity would commit SPOC *and every downstream framework* to that parsing library, so a
later move to another parser would either be blocked or force a major release for a reason
unrelated to the kernel.

`provisional` is exactly the tier for this state: publicly documented, explicitly unsettled,
breakable in a minor release but never in a patch. What settles it is stated on each element —
a downstream framework actually mounting it, which fixes the shape against a real second
caller, or SPOC committing to its parser choice.

*Alternative rejected*: `public` behind a SPOC-owned parameter type (a mount protocol). It is
the durable answer and remains the right one later, but designing that type now means designing
it against an imagined caller. The spec's requirement that a provisional element state its
settling condition is what keeps this from drifting.

*Alternative rejected*: leave all four internal and rely on the how-to's warning. Honest, but
it makes the documented extension point permanently unusable by anyone unwilling to pin an exact
SPOC version, which is the whole downstream story.

### The notice lives on the function, the export lives on the package

Tier derivation reads the package's published namespace; the provisional notice is read from
the element's own documentation, following an alias to whatever it re-exports. So the two
halves are placed where each is read: `register` joins each package's `__all__`, and the
`Provisional:` paragraph goes in the function's own docstring beside the behavior it qualifies.

This keeps the notice one edit away from the code it describes, and means no element's tier
needs a second file — which the surface contract already requires of importable elements.

### Core versus adapter is unchanged

`cli.py` remains a thin adapter in every one of the four packages: it describes commands,
attaches handlers, and holds no generation, diagnostic, projection, or stub logic. Promoting
the mount does not move behavior outward — it states a promise about an adapter that already
had the right shape. Dependencies still point inward: the mount depends on its package's
operations, never the reverse, and `spoc.cli` remains the only place the concrete adapters are
constructed.

### No build-vs-adopt decision arises

The `/ai:decide` gate applies to critical concerns realized by a tool choice. This change adopts
no dependency, writes no new mechanism, and touches no correctness-, security-, or
reliability-sensitive concern — it restates the tier of four existing functions. The one tool
question in the neighborhood, whether to keep the standard library's parser, is explicitly the
question `provisional` defers rather than one this change answers.

## Risks / Trade-offs

- **Promoting four elements enlarges the promised surface, and a promise is easier to make than
  to withdraw.** → `provisional` may break in a minor release, and the withdrawal lifecycle
  applies if it comes to that. The pre-1.0 window is the cheapest moment this decision will ever
  be available.
- **The stated settling condition depends on an event that may never arrive** — a downstream
  framework. → The condition names a second, independent trigger: SPOC committing to its parser
  choice. The checker can only detect a bare hedge, so the honesty of the condition is a review
  obligation, which is why it is written down here.
- **The parser type stays private-to-the-standard-library, so type checkers may flag downstream
  callers.** → Unchanged from today; the how-to shows the working call. Fixing it is the
  `public` option, deferred deliberately.
- **`apidiff` will report four additions to the promised surface in the next release.** → They
  are additions, not breakages; raising a tier is always permitted by the contract.
