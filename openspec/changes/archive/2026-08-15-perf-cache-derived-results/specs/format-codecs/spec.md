# Format Codecs — delta

## MODIFIED Requirements

### Requirement: Formats requiring an optional dependency fail by naming it

A format whose support requires a dependency outside the standard library MUST NOT cause a
failure when the surface is imported. The failure MUST occur when that format is first
requested, and MUST name the optional extra to install. It MUST NOT surface as an unresolved
import from a transitive module.

Formats supported by the standard library MUST remain usable when no optional dependency is
installed at all.

The availability of a format is settled the first time it is probed and MUST remain stable
for the rest of the process: repeated requests for an unavailable format, and repeated
enumerations of supported formats, MUST NOT re-run the dependency discovery that already
failed. A dependency installed while the process is running is observed only by a new
process.

#### Scenario: Import succeeds with nothing optional installed

- **WHEN** the surface is imported in an environment with no optional dependency present
- **THEN** the import succeeds, and no optional dependency is loaded

#### Scenario: Missing extra is reported actionably

- **WHEN** a format is requested whose optional dependency is absent
- **THEN** the operation fails with a message naming the extra required to enable it, rather
  than reporting a missing module

#### Scenario: Standard-library formats work bare

- **WHEN** an environment has no optional dependency installed
- **THEN** every format declared as standard-library-supported reads and writes normally

#### Scenario: Repeated probing does not repeat discovery

- **WHEN** a format whose optional dependency is absent is requested several times, or the
  supported formats are enumerated several times, within one process
- **THEN** the dependency discovery runs at most once per format and direction, and every
  repetition reports the same outcome with the same actionable message

#### Scenario: A mid-process installation is not observed

- **WHEN** a format's optional dependency is installed after that format's availability has
  already been probed in a running process
- **THEN** the running process continues to report the format unavailable, and a new process
  observes it as available
