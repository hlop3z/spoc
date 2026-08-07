## ADDED Requirements

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

#### Scenario: Retrieval failure writes nothing

- **WHEN** a remote reference cannot be retrieved
- **THEN** the operation fails naming the reference and the reason, and no file is created or
  modified at the destination

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

No name used to construct any local path during retrieval may originate from the remote party.
Names supplied by the remote party as metadata about the transfer MUST be ignored entirely.

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

#### Scenario: Remote-supplied names are never used as paths

- **WHEN** the remote party supplies a name for the transferred content
- **THEN** that name is not used to construct any local path, and content that would be written
  outside the intended working location on the strength of it is never written

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

#### Scenario: Weakening redirection is refused

- **WHEN** retrieval of a reference is redirected onto a location offering weaker guarantees
  than the reference as supplied
- **THEN** the retrieval fails naming the refused destination, and nothing is written

### Requirement: A retrieved revision is reusable without retrieving it again

Content retrieved for an exact revision MUST be retained and reused when the same revision is
requested again, so a repeat generation performs no retrieval. A retained revision MUST remain
usable when retrieval is unavailable.

Retention MUST be addressed by the exact revision, so retained content is never stale for the
revision it is retained under.

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
