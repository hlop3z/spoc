# Data Collection

## MODIFIED Requirements

### Requirement: A directory of mixed formats resolves to one mapping

A single collection operation MUST resolve a directory tree containing files of differing
supported formats into one mapping, so that a project reads many sources without invoking a
loader per file. Files whose extension maps to no supported format MUST be skipped rather than
failing the collection, and the set skipped MUST be reportable. An existing empty
directory is a valid, empty collection; a root that does not exist or is not a
directory MUST fail the collection naming the path, so a typo surfaces at the call
rather than as a silently empty result.

Entries whose name marks them as hidden by platform convention (a leading dot) MUST be
skipped by default — files and directories alike — and the collection call MUST accept
explicit ignore patterns that extend the skip set. Skipping happens before key
derivation, so a skipped entry can neither violate the key grammar nor contribute
entries, and the skipped set remains reportable. Loudness is unchanged for everything
actually collected: a collected entry that would produce a non-conforming key still
fails the whole collection.

A skipped directory MUST be skipped as a unit: the collection MUST NOT enumerate,
inspect, or otherwise traverse what it holds. The cost of a collection is therefore set
by the tree it collects rather than by the tree it sits in, so a data directory beside a
version-control or dependency directory costs no more than one standing alone. This is
observable and not merely an optimization — a skipped directory that cannot be read, or
whose contents would be expensive or impossible to enumerate, MUST NOT affect the
collection.

Because a skipped directory is not traversed, the reportable skipped set MUST name the
skipped entry itself — the directory — and MUST NOT name the entries beneath it, which
were never examined and about which the collection has nothing to report. A skipped file
is named as itself, as before.

#### Scenario: Mixed formats collect together

- **WHEN** a directory containing files of several different supported formats is collected
- **THEN** the result is one mapping whose entries include the content of every supported file,
  each normalized to the intermediate representation

#### Scenario: Unsupported files are skipped, not fatal

- **WHEN** a collected directory also contains files of unsupported types
- **THEN** the collection succeeds, those files contribute no entries, and the skipped set is
  reportable

#### Scenario: Nested directories are included

- **WHEN** a directory containing subdirectories of supported files is collected
- **THEN** entries from the nested files are present in the same single mapping

#### Scenario: An empty directory is not an error

- **WHEN** a collection targets an existing directory that is empty
- **THEN** the result is an empty mapping rather than a failure

#### Scenario: An absent root fails loudly

- **WHEN** a collection targets a path that does not exist or is not a directory
- **THEN** the collection fails naming that path, and returns no mapping

#### Scenario: Hidden entries are skipped, not fatal

- **WHEN** the collected tree contains a hidden directory (for example `.cache`)
  holding files of supported formats
- **THEN** the collection succeeds, nothing under that directory contributes an entry,
  and the directory appears in the reportable skipped set

#### Scenario: Explicit ignore patterns extend the skip set

- **WHEN** a collection is invoked with an ignore pattern matching a subdirectory
- **THEN** files under that subdirectory contribute no entries, the subdirectory itself
  appears in the skipped set, no file beneath it appears there, and the rest of the tree
  collects normally

#### Scenario: A skipped directory is not traversed

- **WHEN** a collection runs over a tree containing a skipped directory
- **THEN** no entry beneath that directory is enumerated or inspected, and the collection
  succeeds identically whether that directory holds one file or very many

#### Scenario: An unreadable skipped directory does not affect the collection

- **WHEN** the collected tree contains a hidden or ignored directory whose contents
  cannot be enumerated
- **THEN** the collection still succeeds over the rest of the tree, because the skipped
  directory was never descended

#### Scenario: Collected entries stay loud

- **WHEN** a directory that is neither hidden nor ignored would produce a key segment
  violating the identity grammar
- **THEN** the collection still fails naming the offending value and the grammar
