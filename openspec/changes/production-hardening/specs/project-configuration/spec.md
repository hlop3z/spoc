# Project Configuration — Delta

## MODIFIED Requirements

### Requirement: Mode cascade for app lists

Apps MUST be declared per mode, and the effective app list MUST cascade
according to a declared mode set. The mode set and each mode's cascade order
MUST be declarable in the configuration file; when the configuration declares
none, the default mode set applies: production includes only production apps;
staging includes staging then production; development includes development,
then staging, then production. Order is preserved and duplicates keep first
position. The active mode and every app-group key MUST name a mode in the
effective mode set; an unknown mode MUST fail start naming the valid modes.

#### Scenario: Development includes everything

- **WHEN** the configuration declares production `[auth]`, staging `[admin]`,
  development `[demo]` and the mode is `development`
- **THEN** the effective app list is `demo, admin, auth` in that order

#### Scenario: Production includes only production

- **WHEN** the same configuration runs in `production` mode
- **THEN** the effective app list is exactly `auth`

#### Scenario: Custom mode set

- **WHEN** the configuration declares a mode `test` whose cascade is
  `test, production`, with test apps `[fixtures]` and production apps
  `[auth]`, and the mode is `test`
- **THEN** the effective app list is `fixtures, auth` in that order

#### Scenario: Unknown mode fails naming the valid set

- **WHEN** the active mode or an app-group key names a mode outside the
  effective mode set
- **THEN** start fails with an error naming the offending mode and the modes
  that are valid

## ADDED Requirements

### Requirement: Apps are declared by module path

Every app entry MUST be a dotted module path importable by the language's
normal import mechanism from the environment the project runs in. The
component namespace for an app derives from the final segment of its declared
path, and that segment MUST conform to the identity grammar's namespace rule.
An app path that cannot be imported MUST fail start naming the path; the
kernel MUST NOT alter the import environment to make a path resolvable.

#### Scenario: Namespace derives from the final segment

- **WHEN** an app is declared as `myproject.apps.blog` and its modules declare
  components
- **THEN** those components register under namespace `blog`

#### Scenario: Unimportable app path

- **WHEN** a declared app path cannot be imported
- **THEN** start fails with an error naming the declared path

#### Scenario: Final segment must satisfy the grammar

- **WHEN** a declared app path's final segment violates the namespace grammar
- **THEN** start fails with an error naming the segment and the grammar
