# Static Type Soundness

## Purpose

The contract that the package's published type information is verified, not
asserted. Annotations are part of what a typed distribution ships, so they are
gated by a mature checker at its strictest; the places the source is deliberately
beyond a gradual type system are named, scoped, and countable rather than scattered.

## Requirements

### Requirement: The library source passes a mature checker at its strictest

The published package source MUST pass a mature, widely-deployed static type checker
in its strictest standard mode, as a standing row of the validation gate. A beta or
unreleased checker MAY run beside it but MUST NOT be the only checker gating the
source. When two gating checkers disagree, the disagreement MUST be treated as a
finding about the source, never resolved by loosening whichever checker reported it.

#### Scenario: A typing defect cannot land silently

- **WHEN** a change introduces code the strict gate cannot verify (an untyped
  parameter, an unproven return type, an unparameterized generic)
- **THEN** the validation gate fails, naming the file and line, before the change is
  claimed done

#### Scenario: The gate runs where the code runs

- **WHEN** the validation gate executes on any declared platform and supported
  interpreter
- **THEN** the strict type check runs there with the same configuration and the same
  outcome expectations as on every other leg of the matrix

### Requirement: Registration surfaces preserve static types

Every public surface that registers or marks an object and returns it MUST preserve
the object's static type: a checker reading the call site MUST see the decorated
object's own type, not an erased one. Typing a registration surface to erase what it
returns is a defect — a generated stub deriving from it would promise an erased type
while every runtime assertion still passes.

#### Scenario: A decorated class keeps its type

- **WHEN** a class or function is registered through any public registration surface
  — a kind's registration handle or the low-level marker — bare or parameterized
- **THEN** a static checker sees the registered object at its own declared type at
  the registration site and at every later use

### Requirement: Dynamic escapes are scoped and enumerable

A checker exemption MUST be scoped to the narrowest unit the toolchain allows, where
the source is deliberately dynamic beyond what a gradual type system can model. It
MUST carry an in-place justification naming why the dynamism is the design, and the
full set of such escapes MUST be enumerable from configuration — never scattered as
unexplained inline suppressions.

#### Scenario: An exemption cannot spread

- **WHEN** a new module fails the strict gate for reasons unrelated to a recorded
  escape
- **THEN** the gate fails; the existing exemption's scope does not cover the new
  module, and widening any exemption requires its own recorded justification
