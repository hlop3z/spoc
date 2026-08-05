# Data Collection

## Purpose

A directory tree of mixed formats resolves to one mapping in a single call, so a project
reads many sources without invoking a loader per file. Keys derive from a file's location
rather than its format, which is what makes a collision between two files detectable —
and collisions fail rather than resolve by precedence. Collection is eager and all-or-
nothing, so a malformed file is found at the call rather than at whichever code path first
reads it. The kernel never invokes this surface; removing it entirely leaves startup
unchanged.

## Requirements

### Requirement: A directory of mixed formats resolves to one mapping

A single collection operation MUST resolve a directory tree containing files of differing
supported formats into one mapping, so that a project reads many sources without invoking a
loader per file. Files whose extension maps to no supported format MUST be skipped rather than
failing the collection, and the set skipped MUST be reportable. An existing empty
directory is a valid, empty collection; a root that does not exist or is not a
directory MUST fail the collection naming the path, so a typo surfaces at the call
rather than as a silently empty result.

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

### Requirement: Entry keys derive from location and never collide silently

Each collected entry MUST be keyed by its path relative to the collection root with the format
extension removed and the path separators replaced by dots, so that the same logical name in
different subdirectories produces different keys.

Every segment of a derived key MUST satisfy the same identity grammar the kernel enforces for
component name segments. A file whose name or containing directory would produce a
non-conforming segment MUST fail the collection naming the offending value and the grammar it
must satisfy, rather than producing a key that only approximates it.

When two files would produce the same key — most commonly the same stem in two formats in one
directory — the collection MUST fail naming both conflicting paths. It MUST NOT resolve the
conflict by a format precedence rule, by ordering, or by merging.

#### Scenario: Keys derive from relative location

- **WHEN** a directory tree is collected
- **THEN** each entry's key is that file's path relative to the collection root, extension
  removed and separators rendered as dots, and files of the same stem in different
  subdirectories occupy distinct keys

#### Scenario: A key segment violating the grammar is refused

- **WHEN** a collected file's name or containing directory would produce a key segment that does
  not satisfy the identity grammar
- **THEN** the collection fails naming the offending value and the grammar, and returns no
  mapping

#### Scenario: A dotted filename is refused rather than reinterpreted

- **WHEN** a collected file's stem itself contains a separator that would read as an additional
  key segment
- **THEN** the collection fails rather than silently producing a key with more segments than the
  file's location implies

#### Scenario: Same stem in two formats is refused

- **WHEN** one directory contains two files with the same stem in two different supported
  formats
- **THEN** the collection fails naming both paths, and no partial result is returned

#### Scenario: The key is independent of the source format

- **WHEN** a file is collected and then the same content is collected again from a file of the
  same stem in a different format
- **THEN** both produce the same key, which is what makes the collision in the previous scenario
  detectable

### Requirement: Collection is eager and fails as a whole

A collection operation MUST fully read and normalize every file it collects before returning.
A file that fails to parse MUST fail the collection, naming the offending path and the
underlying reason. A failed collection MUST NOT return a partial mapping.

Deferring parse work until an entry is first accessed MUST NOT be the default behavior, so that
a malformed file is discovered at the collection call rather than at whichever code path first
reads it.

#### Scenario: A malformed file fails the collection

- **WHEN** a directory containing one malformed file of a supported format is collected
- **THEN** the operation fails naming that file and the parse failure, and returns no mapping

#### Scenario: Every entry is parsed before returning

- **WHEN** a collection returns successfully
- **THEN** every entry in the result holds a fully normalized value, and reading any entry
  performs no further parsing and can raise no parse failure

#### Scenario: Enumeration is truthful

- **WHEN** a returned collection is enumerated
- **THEN** the keys present are exactly those whose values are present and loaded, with no key
  that would fail on access and no loaded value absent from enumeration

### Requirement: Collection does not participate in framework startup

The collection surface MUST NOT be invoked by framework startup, and the kernel MUST NOT import
it. Importing the kernel MUST NOT load the data surface or any optional format dependency.
Removing the surface entirely MUST leave framework startup, configuration loading,
discovery, identity, and resolution behaving identically.

#### Scenario: Startup does not load collections

- **WHEN** a framework is started in a project containing collectible data directories
- **THEN** no collection is performed and no optional format dependency is loaded

#### Scenario: Importing the kernel does not load the data surface

- **WHEN** the kernel package is imported without touching the data surface
- **THEN** the data surface's modules are not loaded, and no optional format dependency
  is imported

#### Scenario: The surface is removable

- **WHEN** the data surface is removed from the distribution
- **THEN** the kernel continues to start projects and pass its own suite unchanged

#### Scenario: Install footprint is unchanged

- **WHEN** the package is installed without optional extras
- **THEN** the acquired dependency set is unchanged from the package's stated guarantee
