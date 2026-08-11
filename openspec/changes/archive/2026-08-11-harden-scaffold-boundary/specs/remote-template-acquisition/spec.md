## ADDED Requirements

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
