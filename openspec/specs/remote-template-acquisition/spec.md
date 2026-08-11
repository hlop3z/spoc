# remote-template-acquisition Specification

## Purpose

How a template set named by a location outside the local system is parsed, pinned, retrieved,
bounded, admitted, and retained — everything that happens before a template set exists to be
validated. Retrieved content is treated as hostile throughout: it is written by someone the
user may never have met, so every part of it is admitted rather than trusted.

## Requirements

### Requirement: Every reference resolves by one ordered, total rule

A template set reference MUST resolve to exactly one kind of source, chosen by an explicit
discriminator evaluated in a fixed order. No reference may fall through to a later kind because
an earlier kind failed to load it: failing to resolve and resolving to something that then fails
are distinct outcomes and MUST be reported distinctly.

A reference that resolves to no kind MUST fail naming the reference and the part of it that did
not resolve, and MUST NOT be reported as a missing file, a missing directory, or a missing
manifest.

#### Scenario: Discriminator precedes existence

- **WHEN** a reference is supplied whose form designates a remote location
- **THEN** it is resolved as a remote reference regardless of whether a local file or directory
  of the same literal spelling exists

#### Scenario: Unresolvable reference names the failing part

- **WHEN** a reference is supplied that matches no known form
- **THEN** the operation fails naming the reference and the segment that did not resolve, lists
  the forms that are recognized, and writes nothing

#### Scenario: Resolved but unloadable is a different failure

- **WHEN** a reference resolves to a kind, and loading from that kind then fails
- **THEN** the failure describes what was wrong at that source, and does not claim the reference
  was unrecognized

### Requirement: A remote reference designates an exact revision

A reference to a remote location MUST be resolved to an exact, immutable revision identifier
before any content is retrieved, and generation MUST proceed against that revision. When the
reference names a moving target, the revision it resolved to MUST be reported to the caller.

Two operations naming the same reference and resolving to the same revision MUST produce
identical content.

#### Scenario: Moving reference reports what it resolved to

- **WHEN** a remote reference that names a moving target is used to generate
- **THEN** the operation reports the exact revision it resolved to, in a form that can be
  supplied back as a reference to reproduce the same result

#### Scenario: Pinned reference is reproducible

- **WHEN** two generations are performed with a reference naming the same exact revision
- **THEN** the generated content is identical

### Requirement: Retrieval completes before anything is written

A remote template set MUST be fully retrieved, admitted, and validated before any file is
written to the destination. Failure to retrieve, failure to admit any part of the retrieved
content, or failure to validate the resulting template set MUST leave the destination
untouched.

A failure MUST name the reference in the form the caller supplied it. A location the operation
derived from that reference MAY additionally be reported as detail, but MUST NOT stand in place
of the reference: the caller can only correct what they wrote, and a derived location names
something they never typed.

#### Scenario: Retrieval failure writes nothing

- **WHEN** a remote reference cannot be retrieved
- **THEN** the operation fails naming the reference and the reason, and no file is created or
  modified at the destination

#### Scenario: Failure names what the caller supplied

- **WHEN** retrieval of a remote reference fails at a location the operation derived from that
  reference
- **THEN** the failure names the reference as the caller supplied it, and does not report the
  derived location alone

#### Scenario: Retrieved set is validated like any other

- **WHEN** a retrieved template set omits a required element or declares an unsatisfiable
  substitution value
- **THEN** the operation fails identically to the same defect in a local template set, and
  writes nothing

### Requirement: Retrieved content is admitted, never trusted

Every member of retrieved content MUST be individually admitted before it is materialized.
A member MUST be refused when its path is absolute, when it escapes the location it is being
materialized into by any means including traversal segments and paths sharing a common prefix
with the destination without being contained by it, or when it is not a regular file or
directory.

Containment MUST be decided by path structure, not by string prefix comparison.

Admission MUST NOT depend on a single control. Containment MUST be verified independently of
whatever vetting the platform's own extraction facility performs, so that a defect in that
facility cannot by itself place content outside the destination.

No name used to construct any local path during retrieval may originate from the remote party.
Names supplied by the remote party as metadata about the transfer MUST be ignored entirely.

The container format MUST be determined from the content itself, never from a name.

#### Scenario: Traversing member is refused

- **WHEN** retrieved content contains a member whose path escapes the destination
- **THEN** the operation fails naming that member, and nothing is written to the destination

#### Scenario: Common prefix is not containment

- **WHEN** retrieved content contains a member whose path shares a leading string with the
  destination but is not contained within it
- **THEN** the member is refused

#### Scenario: Non-regular member is refused

- **WHEN** retrieved content contains a member that is not a regular file or directory
- **THEN** the operation fails naming that member, and nothing is written to the destination

#### Scenario: Refused member leaves nothing behind

- **WHEN** a member is refused
- **THEN** no directory or file was created outside the destination on its behalf

#### Scenario: Containment holds when platform vetting does not

- **WHEN** the platform's extraction vetting admits a member whose path escapes the destination
- **THEN** the member is still refused, and nothing is written outside the destination

#### Scenario: Remote-supplied names are never used as paths

- **WHEN** the remote party supplies a name for the transferred content
- **THEN** that name is not used to construct any local path, and content that would be written
  outside the intended working location on the strength of it is never written

#### Scenario: Format is decided by content

- **WHEN** retrieved content's container format disagrees with any name supplied for it
- **THEN** the content itself decides how it is read

### Requirement: Retrieval is bounded

Retrieval MUST refuse content that exceeds a declared bound on expanded size or on member
count, and MUST refuse it before the excess is materialized rather than after. Bounds MUST be
enforced on expanded size, not only on transferred size.

A redirection of the retrieval onto a location whose guarantees are weaker than those of the
reference as supplied MUST be refused.

#### Scenario: Oversized content is refused mid-expansion

- **WHEN** retrieved content expands beyond the declared size bound
- **THEN** expansion stops at the bound, the operation fails naming the bound that was exceeded,
  and nothing is written to the destination

#### Scenario: Excessive member count is refused

- **WHEN** retrieved content contains more members than the declared bound permits
- **THEN** the operation fails naming the bound, and nothing is written to the destination

#### Scenario: A declared size is not trusted

- **WHEN** retrieved content declares a member size smaller than what that member actually
  expands to
- **THEN** the bound is enforced against what actually expands, not against what was declared

#### Scenario: Weakening redirection is refused

- **WHEN** retrieval of a reference is redirected onto a location offering weaker guarantees
  than the reference as supplied
- **THEN** the retrieval fails naming the refused destination, and nothing is written

### Requirement: A retrieved revision is reusable without retrieving it again

Content retrieved for an exact revision MUST be retained and reused when the same revision is
requested again, so a repeat generation performs no retrieval. A retained revision MUST remain
usable when retrieval is unavailable.

Retention MUST be addressed by the exact revision, so retained content is never stale for the
revision it is retained under. An interrupted retention MUST NOT leave a partially populated
revision appearing retained.

#### Scenario: Repeat generation performs no retrieval

- **WHEN** a generation names a revision whose content has already been retained
- **THEN** the generation succeeds without retrieving anything

#### Scenario: Retained revision survives unavailable retrieval

- **WHEN** a generation names a retained revision and retrieval is unavailable
- **THEN** the generation succeeds from retained content

#### Scenario: Unretained revision without retrieval fails actionably

- **WHEN** a generation names a revision that has not been retained and retrieval is unavailable
- **THEN** the operation fails stating that the revision is not retained and that retrieval was
  unavailable, and writes nothing

#### Scenario: Interrupted retention retains nothing

- **WHEN** retrieval of a revision fails partway through being retained
- **THEN** that revision is not reported as retained afterwards

### Requirement: A revision names its own retained content and no other

A revision MUST designate its own retained content and no other's. Retention addresses content
by the exact revision it was retrieved for, so where a revision is used to designate a
retention location, that use MUST be either faithful or refused: a revision that cannot be used
as a location MUST NOT be rewritten into one that could designate content retrieved for a
different revision.

Two distinct revisions MUST NOT resolve to the same retained content. A revision MUST NOT be
usable to designate a location outside the retention root.

#### Scenario: Distinct revisions never share retained content

- **WHEN** content is retained for two distinct revisions
- **THEN** each is retrieved back for its own revision only, and neither is served for the other

#### Scenario: A revision cannot escape the retention root

- **WHEN** a revision is supplied whose form would designate a location outside the retention
  root
- **THEN** no location outside the retention root is read or written, and the operation either
  refuses the revision or confines it without collapsing it onto another revision's content

#### Scenario: An empty revision is refused

- **WHEN** a revision is supplied that is empty, and so designates no content
- **THEN** the operation fails naming the reference, rather than retaining under a substitute
  name that any other empty revision would also produce

### Requirement: Concurrent retention of one revision converges

Two operations retaining the same revision at the same time MUST both succeed, and MUST both
observe content complete for that revision. Because a revision is immutable, whichever copy is
published first is correct for both; the later one MUST NOT fail, MUST NOT partially overwrite
the published copy, and MUST NOT leave staged content behind.

#### Scenario: Simultaneous retention both succeed

- **WHEN** two operations retain the same revision concurrently
- **THEN** both complete successfully and both read content complete for that revision

#### Scenario: The loser of the race leaves nothing behind

- **WHEN** one operation publishes a revision that another was concurrently staging
- **THEN** the second operation's staged content is not left in the retention root

#### Scenario: A retention failure is not disguised as a race

- **WHEN** publishing retained content fails for a reason other than the revision already being
  present
- **THEN** the operation fails rather than reporting the revision as retained

### Requirement: Retained content is located by platform convention and by a stated override

Retained content MUST be placed in the location the host platform designates for per-user
cached data. Where a user has stated where cached data belongs, that statement MUST take
precedence over the platform default on every platform.

The location MUST be namespaced to this project, so that removing it removes only this
project's retained content.

#### Scenario: A stated override wins on every platform

- **WHEN** the user has stated a location for cached data
- **THEN** retained content is placed under that location, on every supported platform

#### Scenario: Each platform's convention is followed

- **WHEN** no override is stated
- **THEN** retained content is placed under the location that host platform designates for
  per-user cached data

#### Scenario: Retention is namespaced to the project

- **WHEN** the retention location is derived
- **THEN** it is contained within a directory identifying this project
