## Context

Two facts, discovered while scoping this change, set its shape.

**The project declares every platform and gates one.** `pyproject.toml` carries
`Operating System :: OS Independent` while every job in `.github/workflows/ci.yml` runs
`ubuntu-latest` and the matrix varies `python-version` alone. Under the new
`platform-support` capability, "OS Independent" is not a declaration that can be satisfied —
no gate can execute on every operating system — so the classifier is the first thing this
change has to make honest.

**The coverage gap and the platform gap are the same gap.** `cache.default_cache_root()`
branches on `sys.platform`. Measured on Windows, the darwin and POSIX arms are dark; measured
on ubuntu, the Windows arm is dark. Neither run can see the whole, and the number each
reports is a property of the host rather than of the code. Raising coverage by running on
more platforms would paper over this: the branch would still be untestable from any single
machine, which is precisely what the spec forbids.

The constraint that shapes everything else: `.canon/checks.md` is the source `Taskfile.yml`
and `.github/workflows/ci.yml` both derive from. Platform scope is therefore a property
recorded in that table, and the two consumers follow it. Adding a leg to CI without stating
it there would make `task check` a weaker gate than CI, which the table exists to prevent.

Architecturally, `remote.py` and `cache.py` are already adapters — the only outbound socket
and the only writes outside the destination, sitting behind the `RevisionResolver`, `Fetcher`,
and `Cache` ports declared in `plan.py`. That split is why the whole remote path is testable
without a server, and this change spends its budget inside that split rather than widening it.
Dependencies continue to point inward; no port grows a new method.

## Goals / Non-Goals

**Goals:**

- Make the declared platform set, the gated platform set, and the documented platform set one
  set.
- Make every platform-conditional branch reachable from any single host, so the coverage
  figure stops depending on where it was measured.
- Turn the documented retrieval invariants — the transfer bound, the redirect refusal along a
  real retrieval, malformed-reference rejection, every revision-resolution form, and URL
  construction per scheme — into exercised ones.
- Correct the lossy revision-to-location mapping so distinct revisions cannot alias.
- Preserve the socket-free property of the test suite without exception.

**Non-Goals:**

- Raising coverage as a number. Lines that are uncovered because they are unreachable stay
  uncovered; if a line cannot be reached, that is a finding about the line, not a gap to fill.
- Live network tests. SPOC's own repository remains the real-GitHub fixture for exploratory
  use; it does not enter the gate.
- Widening the port surface, adding a dependency, or introducing a test framework beyond what
  the suite already uses.
- Re-examining the `keywords = [... "kernel" ...]` entry in `pyproject.toml`, which the recent
  naming correction left behind. Out of scope, flagged rather than fixed here (Rule 7).
- Any change to `spoc.testing`, which is the harness SPOC ships to its users, not the harness
  SPOC tests itself with.

## Decisions

Every build-vs-adopt call below was run through `/ai:decide` and is recorded as an ADR in
`DECISIONS.md` — that file is their canonical home, and the tool names live there. What
follows is the design rationale, not a second copy of the decision.

The gate confirmed rather than overturned the prior *Cache location — Build (thin) on the
platform conventions* ADR: `platformdirs` remains the mature answer, no standard-library
equivalent has landed, and `dependencies = []` still blocks adopting it. It also turned up
one thing worth stating plainly — the mature pytest platform plugins all *skip* tests on the
wrong platform, which is the categorical opposite of what `platform-support` requires, so
adopting one would defeat the requirement rather than serve it.

### D1: Platform selection becomes a value, not an ambient read

`default_cache_root()` is split into a pure function taking the platform identifier and the
environment mapping as arguments, and a thin adapter that reads `sys.platform` and
`os.environ` and delegates. The four branches then become an ordinary parametrized table test
— no patching of interpreter globals, and every branch reachable from every host by
construction.

*Alternatives considered.* Monkeypatching `sys.platform` per test: zero production change, but
it patches a global that other code may have already read, and it leaves branch selection an
ambient effect rather than a value — the thing the spec's "verifiable from any host" clause
exists to remove. Rejected. A filesystem-abstraction library: an external dependency for
fifteen lines of platform convention, against a module whose docstring already records why
that dependency was refused once. Rejected.

*Direction:* the pure function is core, the reader is the adapter. Dependency points inward.

### D2: The revision-to-location mapping becomes total and collision-free

Today a revision is filtered to path-safe characters, and anything that filters to nothing
becomes the literal `invalid`. Both halves are lossy: `feature/x` and `featurex` land on one
entry, and every unusable revision lands on `invalid` together.

The mapping becomes: use the revision verbatim when it is already a safe path segment;
otherwise use `rev-<sha256(revision) truncated>`. An empty revision designates no content and
is refused outright. This is total, collision-free to the strength of the digest, incapable of
traversal, and it introduces no new failure the caller must handle for any revision they can
actually express. It also matches a precedent already in the codebase: `HttpRevisionResolver`
already keys a direct archive URL as `url-<digest>`.

*Alternatives considered.* Refuse every non-path-safe revision: simplest and strictest, but the
revision is not always the caller's to control — it can arrive as a `sha` field in a server's
response — so it converts a server's oddity into the user's error. Rejected. Percent-encoding:
reversible and total, but produces `%` in path segments, which is awkward on the platform where
this cache is least tested. Rejected.

*Reachability, stated plainly:* `parse_reference` does not split a revision containing a
separator out of the location at all, so no user-typed reference reaches the collision today.
This is a latent defect being closed, not a live one being patched, and the fix removes the
dependence on that grammar accident.

### D3: The concurrency race is provoked at the seam, not with threads

`Cache.retain` handles the case where another process publishes the same revision first, by
catching `OSError` from the publish and accepting the entry if it now exists. That branch is
exercised by injecting the failure at the publish seam with the entry pre-created — 
deterministic, no sleeps, no scheduler dependence — plus the negative case where the publish
fails and the entry does *not* exist, which must still raise.

*Alternatives considered.* Two real threads with a barrier: exercises the true interleaving,
but is timing-dependent and would be the one flaky test in a 685-test suite. Rejected as the
primary mechanism; the seam test asserts the same postconditions without the flake.

*Acknowledged limit:* this verifies the handler, not that the underlying publish is atomic on
every filesystem. That is a property of the platform's rename, which the multi-platform gate
now at least exercises for real on each declared platform.

### D4: The matrix widens on the platform-sensitive job only

The `python` job gains a full operating-system dimension across the declared platforms. The
`go`, `docs-build`, and `doc-links` jobs remain single-platform, which the `platform-support`
spec permits for checks whose outcome cannot differ by platform — and the reason is recorded
in `.canon/checks.md` alongside each row rather than left as an inference from the workflow
file.

`fail-fast: false` is already set and matters more now: a failure specific to one platform must
not cancel the evidence from the others.

*Cost.* The repository is public, so additional legs consume no billed minutes; the cost is
queue time, and the legs run in parallel. Excluding individual OS/version combinations to trim
that was considered and rejected — it would make the matrix stop being derivable from a
statement in `checks.md`, which is the property that keeps CI and `task check` the same gate.

### D5: Coverage is reported, not gated — and the reason is recorded

No `fail_under` is introduced. A floor set at today's number ratchets on a metric this change
exists to argue against treating as the target: the lines that mattered here were invariant
lines, and a floor cannot tell those from any others. What replaces it is the `platform-support`
requirement that the measurement no longer depends on its host, which makes an honest
comparison between two runs possible for the first time.

*Alternative considered.* A global `fail_under` at the achieved total: cheap, standard, and
would catch silent erosion. Rejected for this change, and recorded as a live option rather than
a closed one — if erosion is later observed, the argument changes.

### D6: Injectivity is evidenced by a property, not by examples

That distinct revisions never share retained content is a claim over an open input domain, and
the `feature/x` collision survived exactly because no hand-picked example named it. Hypothesis
is already a dev dependency carrying this project's property suite, so the injectivity of the
revision-to-location mapping is stated there as a property. The collisions actually found stay
alongside it as named regression anchors — the property says the mapping is sound, the anchors
say these specific defects do not come back.

### D7: Test placement follows subject, not module

`tests/test_scaffold_remote.py` currently opens by declaring that nothing in it opens a socket,
and covers retrieval, caching, dispatch, redirect policy, and cache root together. Retention is
becoming a subject of its own — location, revision mapping, concurrency — so it moves to
`tests/test_scaffold_cache.py`, and the socket-free declaration is repeated where it now also
applies. Retrieval, resolution, and URL construction stay where they are.

## Risks / Trade-offs

- **A widened matrix surfaces pre-existing Windows or macOS failures, and this change grows.**
  → That is the change working, not failing. Failures found are fixed here if they are in the
  boundary modules; anything outside them is reported and scoped separately rather than
  absorbed silently.
- **Changing the cache key invalidates every currently retained revision.** → Retained content
  is a cache addressed by immutable revisions, and the only effect of a miss is one retrieval.
  No user data lives there. For path-safe revisions — every revision reachable through the
  reference grammar today — the key is unchanged anyway, so in practice nothing is invalidated.
- **The seam-injected race test could pass while the real race stays broken.** → Accepted and
  stated in D3. The mitigation is that the publish path now genuinely executes on each declared
  platform.
- **`Operating System :: OS Independent` → a named list narrows a published claim.** → It
  narrows the *claim* to what is actually evidenced; it removes no support. The package remains
  pure Python with no dependencies and will keep working where it worked before.
- **More legs, more queue time, and a slower signal on every pull request.** → Accepted; the
  legs are parallel and the repository is public, so the cost is latency rather than money.

## Open Questions

None outstanding.

**Resolved during design — the declared platform set is Linux, Windows, and macOS.** The
deciding argument was that `cache.py` carries a darwin arm today, so a declaration omitting
macOS would ship a branch that no gate ever executes — the exact condition this change exists
to end. The matrix is therefore the full product of three operating systems and three Python
versions, with no exclusions, which keeps it derivable from a single statement in
`.canon/checks.md` (D4). `Operating System :: OS Independent` is replaced by the three
corresponding classifiers.
