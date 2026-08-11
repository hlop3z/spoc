## Why

The parts of SPOC that touch the outside world are the least verified parts of it. Retrieval
and retention — the only code that opens a socket and the only code that writes outside the
destination directory — carry the project's most carefully reasoned invariants and the
thinnest evidence that they hold: 75% and 81% line coverage against a 93% package figure
carried by the pure core, which is the part that cannot fail interestingly.

The gap is not a measurement artifact. Requirements already written down in
`remote-template-acquisition` — a weakening redirection is refused, retrieval failures name
what the caller supplied, an interrupted retention retains nothing — are asserted at the
handler or the port, never along the path a real retrieval takes. A specification that no
test exercises is a claim, not a guarantee.

The same gap has a second face. Development happens on Windows and every CI job runs
`ubuntu-latest`, so the platform the author actually uses is ungated and the platform the
gate actually checks is one nobody develops on. The encoding defect corrected last week
lived precisely in that hole. Worse, the hole is invisible to the coverage number: the
platform-conditional branches in retention are counted as covered on whichever host happens
to run the suite and dark on the other, so neither run can see the whole.

Now, because nothing is in flight and the next release would otherwise publish these paths
on the strength of an average.

## What Changes

- **The validation gate runs on more than one platform.** The platform scope of the checks
  becomes an explicit, recorded property rather than an accident of the runner that was
  chosen first. `.canon/checks.md` is the source both `Taskfile.yml` and
  `.github/workflows/ci.yml` derive from, so the scope is stated there and the two consumers
  follow — otherwise `task check` stops being the gate it claims to be.
- **Platform-conditional behavior is exercised regardless of the host.** Branches selected by
  the operating system are verified on any machine that runs the suite, so a developer on one
  platform is not blind to the other and the coverage figure stops depending on where it was
  measured.
- **The documented retrieval invariants become exercised ones.** The transfer bound, the
  refusal to be redirected onto weaker guarantees as observed through a retrieval rather than
  at the handler, the rejection of a malformed remote reference, revision resolution in each
  of its forms, and retrieval-URL construction for every reference scheme.
- **Retention gains the requirements it was already implementing.** A revision string is used
  as a path segment; that it cannot traverse, and what happens when two processes publish the
  same revision at once, are currently properties of the code alone. They become stated
  behavior.
- **One production correction, already found.** Writing the retention requirements surfaced
  that a revision which is not usable as a location is rewritten into a substitute name, and
  the rewrite is lossy: two distinct revisions can be collapsed onto one retained entry. It is
  not reachable through the reference grammar today — a revision containing a separator is not
  split out as a revision at all — so this is a latent defect, not a live one, and containment
  is not affected. It is corrected here rather than left for the input grammar to keep
  accidentally guarding. Everything else in this change is verification of behavior the
  implementation already satisfies; a further failing test is a further defect discovered, and
  is fixed within this change.
- Tests continue to open no sockets. The port split exists so the entire remote path is
  exercisable without a server, and that property is preserved, not traded away for coverage.

## Capabilities

### New Capabilities

- `platform-support`: which platforms the project's behavior is guaranteed on, that the
  validation gate is executed on each of them, and that platform-conditional behavior is
  verifiable from any host rather than only from the platform it selects for.

### Modified Capabilities

- `remote-template-acquisition`: retention gains requirements for a revision used as a path
  segment (a revision that cannot be used as a location is refused rather than sanitized into
  one that names something else), for concurrent retention of the same revision by two
  processes, and for where retained content is located under platform convention and a
  user's stated override.

## Impact

- **Product code**: `src/spoc/scaffold/cache.py` — the revision-to-location mapping is
  corrected. `src/spoc/scaffold/remote.py` is expected to be read, not edited; any edit there
  is a further defect this change surfaced.
- **Tests**: `tests/test_scaffold_remote.py` grows; a peer file may be split off if it stops
  being one subject.
- **The gate**: `.canon/checks.md` (platform scope), `.github/workflows/ci.yml` (matrix), and
  `Taskfile.yml` if the scope statement affects it. CI minutes rise roughly in proportion to
  the added legs.
- **Documentation**: whatever states supported platforms, if it disagrees with what the gate
  now proves (Rule 8).
- **Critical concerns deferred to `/ai:decide`**: how platform-conditional behavior is
  simulated from a foreign host; whether coverage acquires an enforced floor or remains
  reported; how the concurrent-retention race is provoked deterministically; and the breadth
  of the platform matrix against what each leg costs.
