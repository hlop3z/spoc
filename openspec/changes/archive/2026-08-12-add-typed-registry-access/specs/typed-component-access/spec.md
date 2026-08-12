## ADDED Requirements

### Requirement: Typed access MUST return the registered object unchanged

Resolving a component under a caller-supplied type contract MUST return the identical
registered object — never a copy, wrapper, proxy, or newly constructed instance. Typed
access MUST be a pure lookup: it MUST NOT invoke, construct, or otherwise execute the
registered object.

#### Scenario: The same object comes back

- **WHEN** a component is resolved under a type contract it satisfies
- **THEN** the returned object is the identical object that was registered

#### Scenario: A callable component is not invoked

- **WHEN** a callable component is resolved under a type contract
- **THEN** the callable is returned uninvoked
- **AND** no effect of calling it is observed

### Requirement: Typed access MUST check shape and MUST NOT check structure

Typed access MUST verify at access time that the registered object's shape — constructible,
value, or callable — matches the shape the caller's contract expects, and MUST fail loudly
when it does not. Typed access MUST NOT attempt to verify that the object structurally
satisfies the contract's members; that verification belongs to static checking and is
deliberately not duplicated at access time.

#### Scenario: Shape mismatch is refused

- **WHEN** a caller resolves a component under a contract expecting a constructible object
- **AND** the registered object is a value rather than a constructible object
- **THEN** access fails with an error naming the identifier, the expected shape, and the
  actual shape

#### Scenario: Structural difference is not refused at access time

- **WHEN** a caller resolves a component under a contract whose declared members the
  registered object does not provide
- **AND** the shapes match
- **THEN** access succeeds and returns the object
- **AND** no structural inspection of the object is performed

#### Scenario: Shape matches

- **WHEN** a caller resolves a callable component under a contract expecting a callable
- **THEN** access succeeds

### Requirement: Typed access MUST NOT require importing the providing module

A caller MUST be able to obtain a typed reference to a component declared in another
application without importing that application's modules, at access time or at declaration
time. The only coupling typed access introduces between two applications MUST be the
canonical identifier and the caller's own contract.

#### Scenario: Cross-application access stays decoupled

- **WHEN** one application resolves a component belonging to another under a contract the
  first application declares itself
- **THEN** access succeeds
- **AND** the resolving application has not imported the providing application's modules

### Requirement: Typed access MUST fail with the same precision as untyped resolution

When the identifier cannot be resolved, typed access MUST fail exactly as untyped resolution
does — per segment, naming the segment that could not match and the candidates available at
that segment. Adding a type contract MUST NOT coarsen resolution failures.

#### Scenario: Unknown object name under a type contract

- **WHEN** a caller resolves an identifier whose kind and namespace exist but whose object
  name does not, under a type contract
- **THEN** the failure names the object name, its kind, its namespace, and the available
  candidates in that namespace

#### Scenario: Unknown kind under a type contract

- **WHEN** a caller resolves an identifier whose kind is not declared, under a type contract
- **THEN** the failure names the kind and the declared kind set
