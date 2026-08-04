## ADDED Requirements

### Requirement: A missing module resolves against its own kind's optionality

When a declared app does not provide a module for a declared kind, the framework MUST
decide whether that is an error by consulting the optionality stated on that kind alone.
A missing module for a required kind MUST fail start, naming the app, the kind, and the
module that was expected. A missing module for an optional kind MUST be skipped without
error and without appearing in the registry. No framework-wide setting SHALL override
this per-kind decision, so tolerating one absent kind never silently tolerates another.

#### Scenario: Missing module for a required kind

- **WHEN** an app declared in configuration provides no module for a required kind
- **THEN** start fails, naming the app, the kind, and the expected module

#### Scenario: Missing module for an optional kind

- **WHEN** an app declared in configuration provides no module for an optional kind
- **THEN** start proceeds, that app contributes no components of that kind, and no error
  is raised

#### Scenario: Optionality does not leak between kinds

- **WHEN** a framework declares one optional kind and one required kind, and an app
  provides a module for neither
- **THEN** start fails on the required kind alone, and the absent optional kind is not
  reported as an error

#### Scenario: A module that exists but fails to load is always an error

- **WHEN** an app provides a module for an optional kind and loading that module raises
- **THEN** start fails with that error, because the module was present and broken rather
  than absent
