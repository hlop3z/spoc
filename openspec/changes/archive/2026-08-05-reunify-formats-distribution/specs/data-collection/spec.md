# Data Collection — Delta

## MODIFIED Requirements

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
