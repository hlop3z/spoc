# Delta: remote-template-acquisition

## MODIFIED Requirements

### Requirement: A revision names its own retained content and no other

A revision MUST designate its own retained content and no other's. Retention addresses content
by the exact revision it was retrieved for, so where a revision is used to designate a
retention location, that use MUST be either faithful or refused: a revision that cannot be used
as a location MUST NOT be rewritten into one that could designate content retrieved for a
different revision.

Two distinct revisions MUST NOT resolve to the same retained content. A revision MUST NOT be
usable to designate a location outside the retention root.

Whether two locations are the same MUST be judged by the store that holds them, not by the
revisions differing as text. Where a store treats distinguishable names as one location, a
revision MUST be given a derived name unless the store is guaranteed to hold it under the name
supplied. A revision whose name the store would alter, fold, or share MUST take a derived name.

#### Scenario: Distinct revisions never share retained content

- **WHEN** content is retained for two distinct revisions
- **THEN** each is retrieved back for its own revision only, and neither is served for the other

#### Scenario: Sameness is the store's judgement, not the caller's

- **WHEN** two distinct revisions have names the retention store would treat as one location
- **THEN** at most one of them is retained under the name supplied, the other is retained under
  a derived name, and neither is served for the other

#### Scenario: A stored name is the name that was asked for

- **WHEN** a revision is retained under the name supplied rather than a derived one
- **THEN** the location the store creates carries that name unaltered, so a later request for
  the same revision finds it and a request for any other revision does not

#### Scenario: A revision cannot escape the retention root

- **WHEN** a revision is supplied whose form would designate a location outside the retention
  root
- **THEN** no location outside the retention root is read or written, and the operation either
  refuses the revision or confines it without collapsing it onto another revision's content

#### Scenario: An empty revision is refused

- **WHEN** a revision is supplied that is empty, and so designates no content
- **THEN** the operation fails naming the reference, rather than retaining under a substitute
  name that any other empty revision would also produce
