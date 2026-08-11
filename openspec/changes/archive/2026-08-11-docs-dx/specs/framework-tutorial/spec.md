# framework-tutorial

The end-to-end tutorial contract: the documentation demonstrates — not merely asserts —
that a developer can author a small working framework on the kernel, and the test suite
holds the demonstration true.

## ADDED Requirements

### Requirement: The tutorial authors a framework from nothing

The documentation MUST contain a tutorial that starts from an empty directory and, in
reader-authored steps, produces a running framework on the kernel: declaring the kind
set, writing at least one application component, and projecting the registry onto a
transport that serves a real request. Each step MUST show the complete file being
written, and the final step MUST show a real invocation with its actual response.

#### Scenario: A reader follows the tutorial verbatim

- **WHEN** a reader executes the tutorial's steps in order, copying each file as shown
- **THEN** the final invocation produces exactly the response the tutorial displays

#### Scenario: The payoff is observable

- **WHEN** the reader reaches the tutorial's end
- **THEN** they have issued a request against a framework they authored and seen a
  response derived from a component they registered — not a printed identifier list

### Requirement: The tutorial's code is executed by the test suite

The tutorial's accumulated code MUST be assembled and executed by the test suite as
presented — same files, same order — including the final request/response assertion.

#### Scenario: Tutorial drift is caught

- **WHEN** a kernel change breaks any tutorial step or alters the final response
- **THEN** the validation gate fails, naming the tutorial as the broken surface, before
  the documentation can ship stale

### Requirement: The tutorial framework stays dependency-free

The framework built in the tutorial MUST require no third-party packages, so the
tutorial is runnable on a bare install and demonstrates the kernel rather than a stack.

#### Scenario: Bare-install reader

- **WHEN** a reader with only the kernel package installed follows the tutorial
- **THEN** no step asks them to install anything else, and every step runs
